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
