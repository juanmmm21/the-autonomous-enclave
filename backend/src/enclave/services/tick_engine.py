"""Reloj global de la simulación. En cada tick, recorre a todos los agentes
vivos, ejecuta su ciclo Perceive/Think/Act, cobra el coste pasivo de
mantenimiento y emite un `TickEvent` agregado para la telemetría del frontend."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal

from enclave.exceptions import LLMGenerationError
from enclave.models import AgentState, AgentStatus, EconomicIndicators, TickEvent
from enclave.services.agent_runtime import AgentRuntime
from enclave.services.economy import CentralBank, compute_gini_index

logger = logging.getLogger("enclave.tick_engine")

TickListener = Callable[[TickEvent], Awaitable[None]]


class TickEngine:
    def __init__(
        self,
        runtime: AgentRuntime,
        bank: CentralBank,
        energy_price: Decimal,
        on_tick: TickListener | None = None,
    ) -> None:
        self._runtime = runtime
        self._bank = bank
        self._energy_price = energy_price
        self._on_tick = on_tick
        self._agents: dict[str, AgentState] = {}
        self._system_prompts: dict[str, str] = {}
        self._tick = 0

    @property
    def current_tick(self) -> int:
        return self._tick

    @property
    def bank(self) -> CentralBank:
        return self._bank

    def register_agent(self, agent_state: AgentState, system_prompt: str) -> None:
        self._agents[agent_state.agent_id] = agent_state
        self._system_prompts[agent_state.agent_id] = system_prompt
        self._bank.open_account(agent_state.agent_id, agent_state.balance)

    def agent_snapshot(self, agent_id: str) -> AgentState:
        return self._agents[agent_id]

    def all_agent_ids(self) -> list[str]:
        return list(self._agents.keys())

    def set_inference_quota(self, agent_id: str, quota: int) -> AgentState:
        """Consola de Intervención Divina: apagón tecnológico (o ampliación) de
        los slots de inferencia de un agente, con efecto inmediato."""
        updated = self._agents[agent_id].model_copy(update={"inference_quota": quota})
        self._agents[agent_id] = updated
        return updated

    def sync_balances_from_bank(self) -> None:
        """Refresca los snapshots de `AgentState` tras una intervención directa
        sobre el `CentralBank` (devaluación, subvención), sin esperar al próximo tick."""
        for agent_id, balance in self._bank.all_balances().items():
            if agent_id in self._agents:
                self._agents[agent_id] = self._agents[agent_id].model_copy(
                    update={"balance": balance}
                )

    async def run_tick(self) -> TickEvent:
        self._tick += 1

        for agent_id, agent_state in list(self._agents.items()):
            if agent_state.status in (AgentStatus.BANKRUPT, AgentStatus.TERMINATED):
                continue
            self._agents[agent_id] = await self._run_agent_tick(agent_id, agent_state)

        indicators = self._compute_indicators()
        event = TickEvent(
            tick=self._tick,
            timestamp=datetime.now(UTC),
            agents=list(self._agents.values()),
            indicators=indicators,
        )
        if self._on_tick is not None:
            await self._on_tick(event)
        return event

    async def _run_agent_tick(self, agent_id: str, agent_state: AgentState) -> AgentState:
        system_prompt = self._system_prompts[agent_id]
        context = await self._runtime.perceive(agent_state, self._energy_price, self._tick)

        try:
            action = await self._runtime.think(system_prompt, context)
            agent_state = agent_state.model_copy(update={"last_reasoning": action.reasoning})
            agent_state = await self._runtime.act(agent_state, action, self._tick)
        except LLMGenerationError:
            logger.exception("agent %s produced an invalid action on tick %d", agent_id, self._tick)

        _, is_bankrupt = self._bank.apply_passive_tick_cost(agent_id, self._tick)
        agent_state = agent_state.model_copy(update={"balance": self._bank.get_balance(agent_id)})
        if is_bankrupt:
            agent_state = agent_state.model_copy(update={"status": AgentStatus.BANKRUPT})
        return agent_state

    def _compute_indicators(self) -> EconomicIndicators:
        balances = list(self._bank.all_balances().values())
        gdp = float(sum(balances)) if balances else 0.0
        return EconomicIndicators(
            gini_index=compute_gini_index(balances),
            inflation_rate=0.0,
            virtual_gdp=gdp,
            transactions_per_minute=0.0,
        )
