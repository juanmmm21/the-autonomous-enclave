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

        return Transaction(
            transaction_id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            amount=amount,
            reason=reason,
            tick=tick,
            timestamp=datetime.now(UTC),
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

        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            from_agent=agent_id,
            to_agent=CENTRAL_BANK_TREASURY_ID,
            amount=charged if charged > 0 else Decimal("0.01"),
            reason="passive_tick_cost",
            tick=tick,
            timestamp=datetime.now(UTC),
        )
        is_bankrupt = self._balances[agent_id] <= 0
        return transaction, is_bankrupt

    def apply_penalty(self, agent_id: str, penalty: Decimal, tick: int) -> Transaction:
        """Aplica una multa del Agente Juez. Reusa `transfer` hacia el tesoro."""
        return self.transfer(agent_id, CENTRAL_BANK_TREASURY_ID, penalty, "judge_penalty", tick)


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
