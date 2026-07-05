"""Agente Juez: revisa de forma asíncrona los contratos marcados como
`DISPUTED`, determina al agente responsable y ejecuta la multa directamente
sobre el `CentralBank`."""

from __future__ import annotations

import uuid

from enclave.models import JudgeRuling
from enclave.protocols import JudgeBackend
from enclave.services.contracts import ContractRegistry
from enclave.services.economy import CentralBank

_JUDGE_SYSTEM_PROMPT = (
    "Eres el Agente Juez de The Autonomous Enclave. Analizas contratos comerciales "
    "en disputa entre ciudadanos digitales y determinas de forma imparcial quién "
    "incumplió las condiciones pactadas, aplicando una multa proporcional al daño."
)


class JudgeAgent:
    def __init__(
        self, backend: JudgeBackend, contracts: ContractRegistry, bank: CentralBank
    ) -> None:
        self._backend = backend
        self._contracts = contracts
        self._bank = bank

    async def review_disputed_contracts(self, tick: int) -> list[JudgeRuling]:
        rulings: list[JudgeRuling] = []
        for contract in self._contracts.disputed_contracts():
            dispute_context = (
                f"El contrato fue firmado en el tick {contract.created_at_tick} "
                f"entre {contract.party_a} y {contract.party_b} por {contract.amount} SimCoin. "
                f"Términos: {contract.terms}"
            )
            verdict = await self._backend.adjudicate(
                _JUDGE_SYSTEM_PROMPT, contract, dispute_context
            )

            self._bank.apply_penalty(verdict.at_fault_agent, verdict.penalty, tick)
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
