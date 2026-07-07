"""Reloj global de la simulación. En cada tick, recorre a todos los agentes
vivos, ejecuta su ciclo Perceive/Think/Act, cobra el coste pasivo de
mantenimiento y emite un `TickEvent` agregado para la telemetría del frontend.
Cada `ticks_per_day` ticks, comprime las interacciones recientes de cada
agente en un resumen persistido en la memoria vectorial (ciclo de sueño)."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal

from enclave.exceptions import EnclaveError, LLMGenerationError
from enclave.models import (
    AgentState,
    AgentStatus,
    EconomicIndicators,
    JudgeRuling,
    MarketOffer,
    TickEvent,
)
from enclave.protocols import MemoryStore, MessageBroker
from enclave.services.agent_runtime import AgentRuntime
from enclave.services.contracts import ContractRegistry
from enclave.services.economy import CentralBank, compute_energy_price, compute_gini_index
from enclave.services.inference_market import InferenceQuotaLedger

logger = logging.getLogger("enclave.tick_engine")

TickListener = Callable[[TickEvent], Awaitable[None]]

DEFAULT_TICKS_PER_DAY = 10
# Veredictos del Juez retenidos para el feed de actividad económica: acotado
# para que una simulación de días no acumule memoria sin límite.
RECENT_RULINGS_BUFFER_SIZE = 20


class TickEngine:
    def __init__(
        self,
        runtime: AgentRuntime,
        bank: CentralBank,
        memory_store: MemoryStore,
        quota_ledger: InferenceQuotaLedger,
        contracts: ContractRegistry,
        broker: MessageBroker,
        energy_price: Decimal,
        ticks_per_day: int = DEFAULT_TICKS_PER_DAY,
        tick_interval_seconds: float = 5.0,
        on_tick: TickListener | None = None,
    ) -> None:
        self._runtime = runtime
        self._bank = bank
        self._memory = memory_store
        self._quotas = quota_ledger
        self._contracts = contracts
        self._broker = broker
        self._base_energy_price = energy_price
        self._energy_price = energy_price
        self._ticks_per_day = ticks_per_day
        self._tick_interval_seconds = tick_interval_seconds
        self._on_tick = on_tick
        self._agents: dict[str, AgentState] = {}
        self._system_prompts: dict[str, str] = {}
        self._daily_log: dict[str, list[str]] = {}
        self._energy_price_history: list[Decimal] = []
        self._recent_rulings: deque[JudgeRuling] = deque(maxlen=RECENT_RULINGS_BUFFER_SIZE)
        self._tick = 0

    @property
    def current_tick(self) -> int:
        return self._tick

    @property
    def bank(self) -> CentralBank:
        return self._bank

    @property
    def quotas(self) -> InferenceQuotaLedger:
        return self._quotas

    @property
    def current_energy_price(self) -> Decimal:
        return self._energy_price

    @property
    def recent_rulings(self) -> list[JudgeRuling]:
        """Últimos veredictos del Juez, del más reciente al más antiguo."""
        return list(reversed(self._recent_rulings))

    def record_rulings(self, rulings: list[JudgeRuling]) -> None:
        """Retiene los veredictos que el bucle de ticks recibe del Agente Juez,
        en un buffer acotado, para publicarlos en los próximos `TickEvent`."""
        self._recent_rulings.extend(rulings)

    def register_agent(self, agent_state: AgentState, system_prompt: str) -> None:
        self._agents[agent_state.agent_id] = agent_state
        self._system_prompts[agent_state.agent_id] = system_prompt
        self._daily_log[agent_state.agent_id] = []
        self._bank.open_account(agent_state.agent_id, agent_state.balance)
        self._quotas.open_account(agent_state.agent_id, agent_state.inference_quota)

    def agent_snapshot(self, agent_id: str) -> AgentState:
        return self._agents[agent_id]

    def all_agent_ids(self) -> list[str]:
        return list(self._agents.keys())

    def set_inference_quota(self, agent_id: str, quota: int) -> AgentState:
        """Consola de Intervención Divina: apagón tecnológico (o ampliación) de
        los slots de inferencia de un agente, con efecto inmediato."""
        # El snapshot se resuelve antes de tocar el ledger: si el agente no existe,
        # el KeyError sale limpio sin dejar una cuenta fantasma en las cuotas.
        updated = self._agents[agent_id].model_copy(update={"inference_quota": quota})
        self._quotas.set_quota(agent_id, quota)
        self._agents[agent_id] = updated
        return updated

    def apply_energy_shock(self, factor: Decimal) -> Decimal:
        """Consola de Intervención Divina: shock de escasez (factor > 1) o
        abundancia (factor < 1) energética. Desplaza permanentemente el precio
        base sobre el que oscila `compute_energy_price`, con efecto inmediato
        sobre el precio del tick actual."""
        if factor <= 0:
            raise ValueError("energy shock factor must be positive")
        self._base_energy_price = self._base_energy_price * factor
        self._energy_price = self._energy_price * factor
        return self._energy_price

    def adjust_trust(self, agent_id: str, counterparty_id: str, delta: float) -> None:
        """Implementa `TrustLedger`: usado, entre otros, por el Agente Juez para
        penalizar la confianza hacia quien incumple un contrato."""
        if agent_id not in self._agents:
            return
        current = self._agents[agent_id].trust_links.get(counterparty_id, 0.0)
        updated_trust = max(-1.0, min(1.0, current + delta))
        new_links = {**self._agents[agent_id].trust_links, counterparty_id: updated_trust}
        self._agents[agent_id] = self._agents[agent_id].model_copy(
            update={"trust_links": new_links}
        )

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
        self._energy_price = compute_energy_price(self._base_energy_price, self._tick)
        self._energy_price_history.append(self._energy_price)

        for agent_id, agent_state in list(self._agents.items()):
            if agent_state.status in (AgentStatus.BANKRUPT, AgentStatus.TERMINATED):
                continue
            self._agents[agent_id] = await self._run_agent_tick(agent_id, agent_state)

        expired_contracts = self._contracts.expire_overdue_contracts(
            self._tick, self._ticks_per_day
        )
        for contract in expired_contracts:
            logger.info(
                "contract %s auto-escalated to DISPUTED after %d ticks without resolution",
                contract.contract_id,
                self._ticks_per_day,
            )

        if self._tick % self._ticks_per_day == 0:
            await self._run_sleep_cycle()

        event = await self.snapshot_event()
        if self._on_tick is not None:
            await self._on_tick(event)
        return event

    async def snapshot_event(self) -> TickEvent:
        """Construye un `TickEvent` con el estado actual SIN avanzar el reloj.

        Lo usa `run_tick` al final de cada tick y también la API al registrar
        un ciudadano en caliente, para difundirlo por WebSocket al instante en
        vez de esperar al próximo tick natural."""
        return TickEvent(
            tick=self._tick,
            timestamp=datetime.now(UTC),
            agents=list(self._agents.values()),
            indicators=self._compute_indicators(),
            ticks_per_day=self._ticks_per_day,
            market_offers=await self._fetch_market_offers(),
            open_contracts=self._contracts.open_contracts(),
            recent_rulings=self.recent_rulings,
        )

    async def _fetch_market_offers(self) -> list[MarketOffer]:
        """Ofertas abiertas del tablón. Un fallo del broker (Redis caído) degrada
        el feed de mercado a vacío pero no impide emitir el resto del evento."""
        try:
            return await self._broker.fetch_open_offers()
        except Exception:
            logger.exception("failed to fetch open market offers for tick %d", self._tick)
            return []

    async def _run_agent_tick(self, agent_id: str, agent_state: AgentState) -> AgentState:
        system_prompt = self._system_prompts[agent_id]

        if agent_state.status is AgentStatus.SLEEPING:
            # El sueño dura exactamente un tick: al siguiente impulso el agente
            # despierta y vuelve a participar; sin este reset quedaría marcado
            # como dormido para siempre aunque siga actuando.
            agent_state = agent_state.model_copy(update={"status": AgentStatus.ALIVE})

        try:
            context = await self._runtime.perceive(agent_state, self._energy_price, self._tick)
            action = await self._runtime.think(system_prompt, context)
            agent_state = agent_state.model_copy(update={"last_reasoning": action.reasoning})
            agent_state = await self._runtime.act(agent_state, action, self._tick)
            self._daily_log[agent_id].append(f"[tick {self._tick}] {action.reasoning}")
        except LLMGenerationError:
            logger.exception("agent %s produced an invalid action on tick %d", agent_id, self._tick)
        except EnclaveError:
            # Acción sintácticamente válida pero económicamente imposible (fondos o
            # cuota insuficientes, contrato inexistente): se descarta sin efecto.
            logger.exception(
                "agent %s attempted an economically invalid action on tick %d",
                agent_id,
                self._tick,
            )
        except Exception:
            # Fallos de infraestructura (Redis, Qdrant, Ollama caído...) no deben tumbar
            # el tick de toda la colonia por culpa de un único ciudadano.
            logger.exception(
                "agent %s failed to complete tick %d due to an infrastructure error",
                agent_id,
                self._tick,
            )

        _, is_bankrupt = self._bank.apply_passive_tick_cost(agent_id, self._tick)
        agent_state = agent_state.model_copy(
            update={
                "balance": self._bank.get_balance(agent_id),
                "inference_quota": self._quotas.get_quota(agent_id),
            }
        )
        if is_bankrupt:
            agent_state = agent_state.model_copy(update={"status": AgentStatus.BANKRUPT})
        return agent_state

    async def _run_sleep_cycle(self) -> None:
        """Al final de cada jornada simulada, resume las interacciones clave del
        día de cada agente y las persiste en la memoria vectorial, vaciando el
        log intermedio para el día siguiente."""
        day = self._tick // self._ticks_per_day
        for agent_id, entries in self._daily_log.items():
            if not entries:
                continue
            summary = f"Resumen del día {day} para {agent_id}:\n" + "\n".join(entries)
            try:
                await self._memory.store_daily_summary(agent_id, day, summary)
            except Exception:
                logger.exception(
                    "failed to persist daily summary for agent %s on day %d", agent_id, day
                )
            finally:
                self._daily_log[agent_id] = []

    def _compute_indicators(self) -> EconomicIndicators:
        balances = list(self._bank.all_balances().values())
        gdp = float(sum(balances)) if balances else 0.0
        return EconomicIndicators(
            gini_index=compute_gini_index(balances),
            inflation_rate=self._compute_inflation_rate(),
            virtual_gdp=gdp,
            transactions_per_minute=self._compute_transactions_per_minute(),
        )

    def _compute_inflation_rate(self) -> float:
        """Variación del precio de la energía frente al mismo momento del día
        anterior. `0.0` hasta que haya pasado al menos un día completo."""
        if len(self._energy_price_history) <= self._ticks_per_day:
            return 0.0

        current_price = float(self._energy_price_history[-1])
        price_one_day_ago = float(self._energy_price_history[-1 - self._ticks_per_day])
        if price_one_day_ago == 0:
            return 0.0
        return (current_price - price_one_day_ago) / price_one_day_ago

    def _compute_transactions_per_minute(self) -> float:
        """Volumen real de transacciones del ledger normalizado a un ritmo por
        minuto, usando la ventana de ticks equivalente a los últimos 60s reales."""
        if self._tick_interval_seconds <= 0:
            return 0.0

        window_ticks = max(1, round(60 / self._tick_interval_seconds))
        window_start_tick = max(1, self._tick - window_ticks + 1)
        transaction_count = len(self._bank.transactions_since(window_start_tick))

        ticks_covered = min(self._tick, window_ticks)
        minutes_covered = (ticks_covered * self._tick_interval_seconds) / 60
        if minutes_covered <= 0:
            return 0.0
        return transaction_count / minutes_covered
