"""Dobles de prueba compartidos: implementaciones en memoria de los `Protocol`
de dominio, sin dependencias externas (Redis, Ollama)."""

from __future__ import annotations

from enclave.models import ActionType, AgentAction, InboxMessage, MarketOffer, PerceivedContext


class FakeBroker:
    """Doble en memoria de `MessageBroker`, sin dependencia de Redis."""

    def __init__(self) -> None:
        self.sent_messages: list[InboxMessage] = []
        self.published_offers: list[MarketOffer] = []
        self._inbox: dict[str, list[InboxMessage]] = {}

    async def send_direct_message(self, to_agent: str, message: InboxMessage) -> None:
        self.sent_messages.append(message)
        self._inbox.setdefault(to_agent, []).append(message)

    async def fetch_inbox(self, agent_id: str) -> list[InboxMessage]:
        return self._inbox.pop(agent_id, [])

    async def publish_offer(self, offer: MarketOffer) -> None:
        self.published_offers.append(offer)

    async def fetch_open_offers(self) -> list[MarketOffer]:
        return list(self.published_offers)


class FakeLLM:
    """Doble de `LLMBackend` que devuelve una acción prefijada, sin llamar a Ollama."""

    def __init__(self, action: AgentAction | None = None) -> None:
        self._action = action or AgentAction(action_type=ActionType.IDLE, reasoning="noop")
        self.received_context: PerceivedContext | None = None

    async def generate_action(self, system_prompt: str, context: PerceivedContext) -> AgentAction:
        self.received_context = context
        return self._action


class FakeMemoryStore:
    """Doble en memoria de `MemoryStore`, sin dependencia de Qdrant/Ollama."""

    def __init__(self) -> None:
        self.stored_summaries: list[tuple[str, int, str]] = []
        self._by_agent: dict[str, list[str]] = {}

    async def store_daily_summary(self, agent_id: str, day: int, summary: str) -> str:
        self.stored_summaries.append((agent_id, day, summary))
        self._by_agent.setdefault(agent_id, []).append(summary)
        return f"fake-vector-{len(self.stored_summaries)}"

    async def retrieve_relevant_memories(
        self, agent_id: str, query: str, top_k: int = 5
    ) -> list[str]:
        return self._by_agent.get(agent_id, [])[-top_k:]
