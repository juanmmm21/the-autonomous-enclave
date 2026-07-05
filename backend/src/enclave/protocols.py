"""Interfaces de dominio. Las implementaciones concretas viven en `services/` y
son intercambiables tras estos `Protocol` (p.ej. sustituir Ollama por otro
runtime de inferencia sin tocar el tick engine ni los agentes)."""

from __future__ import annotations

from typing import Protocol

from enclave.models import (
    AgentAction,
    Contract,
    InboxMessage,
    JudgeVerdict,
    MarketOffer,
    PerceivedContext,
)


class LLMBackend(Protocol):
    """Runtime de inferencia usado por cada ciudadano digital en la fase Think."""

    async def generate_action(self, system_prompt: str, context: PerceivedContext) -> AgentAction:
        """Invoca al modelo con la personalidad del agente y su contexto percibido,
        y devuelve una acción ya validada contra el esquema `AgentAction`."""
        ...


class JudgeBackend(Protocol):
    """Runtime de inferencia usado por el Agente Juez para resolver disputas."""

    async def adjudicate(
        self, system_prompt: str, contract: Contract, dispute_context: str
    ) -> JudgeVerdict:
        """Analiza el contrato y el contexto de la disputa, y devuelve un
        veredicto validado contra el esquema `JudgeVerdict`."""
        ...


class MemoryStore(Protocol):
    """Base vectorial persistente para el ciclo de sueño (compresión de memoria)."""

    async def store_daily_summary(self, agent_id: str, day: int, summary: str) -> str:
        """Embebe y persiste el resumen de la jornada. Devuelve el id del vector."""
        ...

    async def retrieve_relevant_memories(
        self, agent_id: str, query: str, top_k: int = 5
    ) -> list[str]:
        """Recupera los `top_k` recuerdos más relevantes para inyectar en el próximo prompt."""
        ...


class MessageBroker(Protocol):
    """Bróker de mensajería para bandejas de entrada privadas y el tablón del mercado."""

    async def send_direct_message(self, to_agent: str, message: InboxMessage) -> None: ...

    async def fetch_inbox(self, agent_id: str) -> list[InboxMessage]: ...

    async def publish_offer(self, offer: MarketOffer) -> None: ...

    async def fetch_open_offers(self) -> list[MarketOffer]: ...

    async def withdraw_offer(self, offer_id: str) -> None: ...


class TrustLedger(Protocol):
    """Permite ajustar la confianza de un agente hacia otro tras un evento
    social relevante (p.ej. un veredicto del Agente Juez)."""

    def adjust_trust(self, agent_id: str, counterparty_id: str, delta: float) -> None:
        """Suma `delta` (puede ser negativo) a la confianza de `agent_id` hacia
        `counterparty_id`, saturando el resultado en el rango [-1, 1]."""
        ...


class ResourceLedger(Protocol):
    """Recursos escasos distintos del SimCoin que los agentes subastan entre sí
    (hoy, cuotas de inferencia; ver `docs/vision.md`)."""

    def transfer_inference_quota(self, from_agent: str, to_agent: str, quantity: int) -> None:
        """Mueve `quantity` unidades de cuota de inferencia entre dos agentes.
        Lanza `InsufficientResourceError` si el vendedor no dispone de tanta."""
        ...
