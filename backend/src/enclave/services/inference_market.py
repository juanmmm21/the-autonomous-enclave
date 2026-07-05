"""Ledger de cuotas de inferencia: el recurso de cómputo escaso que los
agentes subastan entre sí (ver `docs/vision.md`, "Cuotas de Inferencia").
Es un servicio par de `CentralBank`, no una extensión suya, porque se mide
en unidades enteras de cómputo, no en SimCoin."""

from __future__ import annotations

from enclave.exceptions import InsufficientResourceError

RESOURCE_NAME = "inference_quota"


class InferenceQuotaLedger:
    def __init__(self) -> None:
        self._quotas: dict[str, int] = {}

    def open_account(self, agent_id: str, initial_quota: int) -> None:
        self._quotas[agent_id] = initial_quota

    def get_quota(self, agent_id: str) -> int:
        try:
            return self._quotas[agent_id]
        except KeyError as exc:
            raise KeyError(f"no inference quota account open for agent {agent_id}") from exc

    def set_quota(self, agent_id: str, quota: int) -> None:
        """Consola de Intervención Divina: fija la cuota directamente (apagón
        tecnológico o ampliación), sin que medie una transferencia entre agentes."""
        if quota < 0:
            raise ValueError("inference quota cannot be negative")
        self._quotas[agent_id] = quota

    def transfer_inference_quota(self, from_agent: str, to_agent: str, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        available = self.get_quota(from_agent)
        if available < quantity:
            raise InsufficientResourceError(from_agent, RESOURCE_NAME, quantity, available)

        self._quotas[from_agent] = available - quantity
        self._quotas[to_agent] = self._quotas.get(to_agent, 0) + quantity

    def all_quotas(self) -> dict[str, int]:
        return dict(self._quotas)
