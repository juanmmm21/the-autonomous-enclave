"""Ciclo Perceive -> Think -> Act de un único agente para un tick dado.
El `TickEngine` invoca `AgentRuntime.run_tick` para cada ciudadano vivo."""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from enclave.exceptions import LLMGenerationError
from enclave.models import (
    ActionType,
    AgentAction,
    AgentState,
    AgentStatus,
    InboxMessage,
    MarketOffer,
    PerceivedContext,
    Position,
)
from enclave.protocols import LLMBackend, MemoryStore, MessageBroker
from enclave.services.contracts import ContractRegistry
from enclave.services.economy import CentralBank

RECENT_MEMORIES_TOP_K = 3


def _require_str(payload: dict[str, str | int | float], key: str, action: ActionType) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise LLMGenerationError(f"action {action} requires a non-empty string field '{key}'")
    return value


def _require_decimal(
    payload: dict[str, str | int | float], key: str, action: ActionType
) -> Decimal:
    value = payload.get(key)
    if value is None:
        raise LLMGenerationError(f"action {action} requires numeric field '{key}'")
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise LLMGenerationError(f"action {action} field '{key}' is not a valid amount") from exc


class AgentRuntime:
    """Orquesta el ciclo de vida de un agente dentro de un tick."""

    def __init__(
        self,
        llm_backend: LLMBackend,
        broker: MessageBroker,
        bank: CentralBank,
        contracts: ContractRegistry,
        memory_store: MemoryStore,
    ) -> None:
        self._llm = llm_backend
        self._broker = broker
        self._bank = bank
        self._contracts = contracts
        self._memory = memory_store

    async def perceive(
        self, agent_state: AgentState, energy_price: Decimal, tick: int
    ) -> PerceivedContext:
        inbox = await self._broker.fetch_inbox(agent_state.agent_id)
        offers = await self._broker.fetch_open_offers()
        recent_memories = await self._memory.retrieve_relevant_memories(
            agent_state.agent_id, query=agent_state.display_name, top_k=RECENT_MEMORIES_TOP_K
        )
        return PerceivedContext(
            self_state=agent_state,
            inbox=inbox,
            market_offers=offers,
            energy_price=energy_price,
            current_tick=tick,
            recent_memories=recent_memories,
        )

    async def think(self, system_prompt: str, context: PerceivedContext) -> AgentAction:
        return await self._llm.generate_action(system_prompt, context)

    async def act(self, agent_state: AgentState, action: AgentAction, tick: int) -> AgentState:
        """Aplica los efectos de `action` sobre el mundo y devuelve el `AgentState`
        actualizado (posición). Los efectos financieros se aplican directamente
        sobre el `CentralBank` inyectado."""
        agent_id = agent_state.agent_id
        payload = action.payload

        match action.action_type:
            case ActionType.MOVE:
                new_x = int(payload.get("x", agent_state.position.x))
                new_y = int(payload.get("y", agent_state.position.y))
                try:
                    new_position = Position(x=new_x, y=new_y)
                except ValidationError as exc:
                    raise LLMGenerationError(
                        f"move action targeted an out-of-bounds position ({new_x}, {new_y})"
                    ) from exc
                return agent_state.model_copy(update={"position": new_position})

            case ActionType.SEND_MESSAGE:
                to_agent = _require_str(payload, "to_agent", action.action_type)
                body = _require_str(payload, "body", action.action_type)
                await self._broker.send_direct_message(
                    to_agent,
                    InboxMessage(
                        message_id=str(uuid.uuid4()),
                        from_agent=agent_id,
                        to_agent=to_agent,
                        body=body,
                        tick=tick,
                    ),
                )
                return agent_state

            case ActionType.POST_OFFER:
                asset_type = _require_str(payload, "asset_type", action.action_type)
                quantity = int(payload.get("quantity", 0))
                unit_price = _require_decimal(payload, "unit_price", action.action_type)
                if quantity <= 0:
                    raise LLMGenerationError("post_offer requires a positive integer 'quantity'")
                await self._broker.publish_offer(
                    MarketOffer(
                        offer_id=str(uuid.uuid4()),
                        seller_id=agent_id,
                        asset_type=asset_type,  # type: ignore[arg-type]
                        quantity=quantity,
                        unit_price=unit_price,
                        created_at_tick=tick,
                    )
                )
                return agent_state

            case ActionType.ACCEPT_OFFER | ActionType.TRANSFER:
                to_agent = _require_str(payload, "to_agent", action.action_type)
                amount = _require_decimal(payload, "amount", action.action_type)
                self._bank.transfer(agent_id, to_agent, amount, action.action_type.value, tick)
                return agent_state

            case ActionType.SIGN_CONTRACT:
                counterparty = _require_str(payload, "counterparty", action.action_type)
                terms = _require_str(payload, "terms", action.action_type)
                amount = _require_decimal(payload, "amount", action.action_type)
                self._contracts.create_contract(agent_id, counterparty, terms, amount, tick)
                return agent_state

            case ActionType.FILE_DISPUTE:
                contract_id = _require_str(payload, "contract_id", action.action_type)
                self._contracts.mark_disputed(contract_id)
                return agent_state

            case ActionType.SLEEP:
                return agent_state.model_copy(update={"status": AgentStatus.SLEEPING})

            case ActionType.IDLE:
                return agent_state
