"""Registro de contratos comerciales. Vive en memoria junto al `CentralBank`;
el Agente Juez (`judge.py`) resuelve los contratos marcados como `DISPUTED`."""

from __future__ import annotations

import uuid
from decimal import Decimal

from enclave.exceptions import EnclaveError
from enclave.models import Contract, ContractStatus


class ContractNotFoundError(EnclaveError):
    def __init__(self, contract_id: str) -> None:
        self.contract_id = contract_id
        super().__init__(f"contract {contract_id} not found")


class ContractRegistry:
    def __init__(self) -> None:
        self._contracts: dict[str, Contract] = {}

    def create_contract(
        self, party_a: str, party_b: str, terms: str, amount: Decimal, tick: int
    ) -> Contract:
        contract = Contract(
            contract_id=str(uuid.uuid4()),
            party_a=party_a,
            party_b=party_b,
            terms=terms,
            amount=amount,
            status=ContractStatus.PENDING,
            created_at_tick=tick,
        )
        self._contracts[contract.contract_id] = contract
        return contract

    def get(self, contract_id: str) -> Contract:
        try:
            return self._contracts[contract_id]
        except KeyError as exc:
            raise ContractNotFoundError(contract_id) from exc

    def mark_fulfilled(self, contract_id: str) -> Contract:
        contract = self.get(contract_id).model_copy(update={"status": ContractStatus.FULFILLED})
        self._contracts[contract_id] = contract
        return contract

    def mark_disputed(self, contract_id: str) -> Contract:
        contract = self.get(contract_id).model_copy(update={"status": ContractStatus.DISPUTED})
        self._contracts[contract_id] = contract
        return contract

    def mark_breached(self, contract_id: str) -> Contract:
        contract = self.get(contract_id).model_copy(update={"status": ContractStatus.BREACHED})
        self._contracts[contract_id] = contract
        return contract

    def disputed_contracts(self) -> list[Contract]:
        return [c for c in self._contracts.values() if c.status == ContractStatus.DISPUTED]
