"""Agente Juez: revisa de forma asíncrona los contratos marcados como
`DISPUTED`, determina al agente responsable a partir del historial real de
transacciones entre las partes, ejecuta la multa sobre el `CentralBank` y
penaliza la confianza de la parte perjudicada hacia quien incumplió."""

from __future__ import annotations

import logging
import uuid

from enclave.models import JudgeRuling
from enclave.protocols import JudgeBackend, TrustLedger
from enclave.services.contracts import ContractRegistry
from enclave.services.economy import CentralBank

logger = logging.getLogger("enclave.judge")

_JUDGE_SYSTEM_PROMPT = (
    "Eres el Agente Juez de The Autonomous Enclave. Analizas contratos comerciales "
    "en disputa entre ciudadanos digitales y determinas de forma imparcial quién "
    "incumplió las condiciones pactadas, aplicando una multa proporcional al daño. "
    "Tu veredicto de 'at_fault_agent' debe ser exactamente el id de una de las dos "
    "partes del contrato, nunca un tercero."
)

TRUST_PENALTY_ON_BREACH = -0.3


class JudgeAgent:
    def __init__(
        self,
        backend: JudgeBackend,
        contracts: ContractRegistry,
        bank: CentralBank,
        trust_ledger: TrustLedger,
    ) -> None:
        self._backend = backend
        self._contracts = contracts
        self._bank = bank
        self._trust = trust_ledger

    async def review_disputed_contracts(self, tick: int) -> list[JudgeRuling]:
        rulings: list[JudgeRuling] = []
        for contract in self._contracts.disputed_contracts():
            history = self._bank.transactions_between(contract.party_a, contract.party_b)
            history_lines = [
                f"- tick {t.tick}: {t.from_agent} -> {t.to_agent} ({t.amount} SimCoin, {t.reason})"
                for t in history
            ]
            history_text = (
                "\n".join(history_lines) or "No hay transacciones registradas entre las partes."
            )
            dispute_context = (
                f"El contrato fue firmado en el tick {contract.created_at_tick} "
                f"entre {contract.party_a} y {contract.party_b} por {contract.amount} SimCoin. "
                f"Términos: {contract.terms}\n"
                f"Historial de transacciones entre ambas partes:\n{history_text}"
            )
            verdict = await self._backend.adjudicate(
                _JUDGE_SYSTEM_PROMPT, contract, dispute_context
            )

            valid_parties = {contract.party_a, contract.party_b}
            if verdict.at_fault_agent not in valid_parties:
                logger.error(
                    "judge verdict for contract %s named a non-party at fault: %s",
                    contract.contract_id,
                    verdict.at_fault_agent,
                )
                continue

            injured_party = (
                contract.party_b if verdict.at_fault_agent == contract.party_a else contract.party_a
            )

            self._bank.apply_penalty(verdict.at_fault_agent, verdict.penalty, tick)
            self._trust.adjust_trust(injured_party, verdict.at_fault_agent, TRUST_PENALTY_ON_BREACH)
            self._contracts.mark_breached(contract.contract_id)

            rulings.append(
                JudgeRuling(
                    ruling_id=str(uuid.uuid4()),
                    contract_id=contract.contract_id,
                    at_fault_agent=verdict.at_fault_agent,
                    verdict=verdict.verdict,
                    penalty=verdict.penalty,
                    ruled_at_tick=tick,
                )
            )
        return rulings
