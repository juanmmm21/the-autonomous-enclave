"""Excepciones de dominio. Se capturan en los bordes (tick engine, API) para
convertirse en logs y respuestas de error consistentes, nunca se silencian."""

from __future__ import annotations


class EnclaveError(Exception):
    """Raíz de todas las excepciones de dominio del enclave."""


class LLMGenerationError(EnclaveError):
    """El backend de inferencia falló o devolvió una acción que no cumple el esquema."""


class InsufficientFundsError(EnclaveError):
    """Un agente no tiene balance suficiente para completar una transacción."""

    def __init__(self, agent_id: str, required: str, available: str) -> None:
        self.agent_id = agent_id
        self.required = required
        self.available = available
        super().__init__(f"agent {agent_id} needs {required} SimCoin but only has {available}")


class InsufficientResourceError(EnclaveError):
    """Un agente no dispone de suficiente cantidad de un recurso (p.ej. cuota de
    inferencia) para completar una transferencia."""

    def __init__(self, agent_id: str, resource: str, required: int, available: int) -> None:
        self.agent_id = agent_id
        self.resource = resource
        self.required = required
        self.available = available
        super().__init__(
            f"agent {agent_id} needs {required} units of {resource} but only has {available}"
        )


class ContractViolationError(EnclaveError):
    """Un contrato fue incumplido y se remite al Agente Juez."""

    def __init__(self, contract_id: str, reason: str) -> None:
        self.contract_id = contract_id
        self.reason = reason
        super().__init__(f"contract {contract_id} violated: {reason}")
