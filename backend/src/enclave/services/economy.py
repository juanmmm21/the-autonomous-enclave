"""Banco Central: ledger de balances en SimCoin, coste pasivo por tick y
detección de bancarrota. Vive en memoria por ahora (un proceso, un tick engine);
si el enclave crece a múltiples procesos, este ledger se respalda en Postgres
sin cambiar la interfaz pública de `CentralBank`."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from enclave.exceptions import InsufficientFundsError
from enclave.models import Transaction

CENTRAL_BANK_TREASURY_ID = "central_bank_treasury"


class CentralBank:
    def __init__(self, passive_tick_cost: Decimal) -> None:
        self._passive_tick_cost = passive_tick_cost
        self._balances: dict[str, Decimal] = {CENTRAL_BANK_TREASURY_ID: Decimal("0")}
        self._ledger: list[Transaction] = []

    def _record(self, transaction: Transaction) -> Transaction:
        self._ledger.append(transaction)
        return transaction

    def transactions_between(self, agent_a: str, agent_b: str) -> list[Transaction]:
        """Historial completo entre dos partes, en cualquier dirección, ordenado
        por tick. Lo usa el Agente Juez como evidencia al resolver una disputa."""
        parties = {agent_a, agent_b}
        return sorted(
            (
                transaction
                for transaction in self._ledger
                if {transaction.from_agent, transaction.to_agent} <= parties
            ),
            key=lambda transaction: transaction.tick,
        )

    def open_account(self, agent_id: str, initial_balance: Decimal) -> None:
        self._balances[agent_id] = initial_balance

    def get_balance(self, agent_id: str) -> Decimal:
        try:
            return self._balances[agent_id]
        except KeyError as exc:
            raise KeyError(f"no account open for agent {agent_id}") from exc

    def all_balances(self) -> dict[str, Decimal]:
        return {
            agent_id: balance
            for agent_id, balance in self._balances.items()
            if agent_id != CENTRAL_BANK_TREASURY_ID
        }

    def transfer(
        self, from_agent: str, to_agent: str, amount: Decimal, reason: str, tick: int
    ) -> Transaction:
        if amount <= 0:
            raise ValueError("transfer amount must be positive")
        available = self.get_balance(from_agent)
        if available < amount:
            raise InsufficientFundsError(from_agent, str(amount), str(available))

        self._balances[from_agent] = available - amount
        self._balances[to_agent] = self._balances.get(to_agent, Decimal("0")) + amount

        return self._record(
            Transaction(
                transaction_id=str(uuid.uuid4()),
                from_agent=from_agent,
                to_agent=to_agent,
                amount=amount,
                reason=reason,
                tick=tick,
                timestamp=datetime.now(UTC),
            )
        )

    def apply_passive_tick_cost(self, agent_id: str, tick: int) -> tuple[Transaction, bool]:
        """Debita el coste pasivo del tick (mantenimiento/consumo eléctrico).

        Devuelve la transacción generada y si el agente queda en bancarrota
        (balance resultante <= 0). El balance nunca queda negativo: el coste
        real cobrado es como mucho lo que el agente tenía disponible.
        """
        balance = self.get_balance(agent_id)
        charged = min(self._passive_tick_cost, balance) if balance > 0 else Decimal("0")

        self._balances[agent_id] = balance - charged
        self._balances[CENTRAL_BANK_TREASURY_ID] += charged

        transaction = self._record(
            Transaction(
                transaction_id=str(uuid.uuid4()),
                from_agent=agent_id,
                to_agent=CENTRAL_BANK_TREASURY_ID,
                amount=charged,
                reason="passive_tick_cost",
                tick=tick,
                timestamp=datetime.now(UTC),
            )
        )
        is_bankrupt = self._balances[agent_id] <= 0
        return transaction, is_bankrupt

    def apply_penalty(self, agent_id: str, penalty: Decimal, tick: int) -> Transaction:
        """Aplica una multa del Agente Juez. Reusa `transfer` hacia el tesoro."""
        return self.transfer(agent_id, CENTRAL_BANK_TREASURY_ID, penalty, "judge_penalty", tick)

    def print_subsidy(self, agent_id: str, amount: Decimal, tick: int) -> Transaction:
        """Consola de Intervención Divina: inyecta SimCoin nuevo a un agente
        (expansión monetaria), sin debitar el tesoro."""
        if amount <= 0:
            raise ValueError("subsidy amount must be positive")

        self._balances[agent_id] = self.get_balance(agent_id) + amount
        return self._record(
            Transaction(
                transaction_id=str(uuid.uuid4()),
                from_agent=CENTRAL_BANK_TREASURY_ID,
                to_agent=agent_id,
                amount=amount,
                reason="divine_subsidy",
                tick=tick,
                timestamp=datetime.now(UTC),
            )
        )

    def devalue_currency(self, factor: Decimal) -> None:
        """Consola de Intervención Divina: multiplica todos los balances de
        ciudadanos (no el tesoro) por `factor` (p.ej. 0.5 devalúa un 50%)."""
        if factor <= 0:
            raise ValueError("devaluation factor must be positive")

        for agent_id in self.all_balances():
            self._balances[agent_id] = self._balances[agent_id] * factor


def compute_gini_index(balances: list[Decimal]) -> float:
    """Índice de Gini clásico sobre una lista de balances no negativos.

    0.0 = igualdad perfecta, 1.0 = concentración total de la riqueza.
    Con menos de dos agentes con balance positivo se define como 0.0
    (no hay desigualdad que medir).
    """
    positive_balances = sorted(float(b) for b in balances if b > 0)
    n = len(positive_balances)
    if n < 2:
        return 0.0

    total = sum(positive_balances)
    if total == 0:
        return 0.0

    cumulative_weighted_sum = sum((i + 1) * balance for i, balance in enumerate(positive_balances))
    return (2 * cumulative_weighted_sum) / (n * total) - (n + 1) / n
