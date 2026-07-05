import asyncio
from decimal import Decimal

import pytest
from conftest import FakeBroker, FakeLedgerStore, FakeLLM, FakeMemoryStore

from enclave.main import _tick_loop
from enclave.models import (
    ActionType,
    AgentAction,
    AgentState,
    AgentStatus,
    PerceivedContext,
    Personality,
    Position,
)
from enclave.services.agent_runtime import AgentRuntime
from enclave.services.contracts import ContractRegistry
from enclave.services.economy import CentralBank
from enclave.services.inference_market import InferenceQuotaLedger
from enclave.services.tick_engine import TickEngine


class _BrokenBroker(FakeBroker):
    """Simula un fallo de infraestructura (p.ej. Redis caído) durante Perceive."""

    async def fetch_inbox(self, agent_id: str) -> list:  # type: ignore[type-arg]
        raise ConnectionError("redis is unreachable")


def _make_agent_state(agent_id: str) -> AgentState:
    return AgentState(
        agent_id=agent_id,
        display_name=agent_id,
        personality=[Personality.AMBITIOUS],
        balance=Decimal("50.0"),
        inference_quota=3,
        position=Position(x=0, y=0),
    )


def _make_engine(
    broker: FakeBroker | None = None,
    memory_store: FakeMemoryStore | None = None,
    ticks_per_day: int = 3,
    tick_interval_seconds: float = 5.0,
    llm: FakeLLM | None = None,
    contracts: ContractRegistry | None = None,
) -> tuple[TickEngine, FakeMemoryStore, ContractRegistry]:
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    quotas = InferenceQuotaLedger()
    contract_registry = contracts or ContractRegistry()
    memory = memory_store or FakeMemoryStore()
    runtime = AgentRuntime(
        llm or FakeLLM(), broker or FakeBroker(), bank, contract_registry, memory, quotas
    )
    engine = TickEngine(
        runtime,
        bank,
        memory,
        quotas,
        contract_registry,
        energy_price=Decimal("1.0"),
        ticks_per_day=ticks_per_day,
        tick_interval_seconds=tick_interval_seconds,
    )
    return engine, memory, contract_registry


async def test_run_tick_charges_passive_cost_to_registered_agents() -> None:
    engine, _, _ = _make_engine()
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    await engine.run_tick()

    assert engine.agent_snapshot("agent-1").balance == Decimal("49.0")


async def test_run_tick_survives_infrastructure_failure_in_perceive() -> None:
    engine, _, _ = _make_engine(broker=_BrokenBroker())
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    event = await engine.run_tick()

    # El agente sigue existiendo y paga su coste pasivo pese al fallo de Redis.
    assert engine.agent_snapshot("agent-1").balance == Decimal("49.0")
    assert event.tick == 1


async def test_sleep_cycle_persists_daily_summary_at_day_boundary() -> None:
    engine, memory, _ = _make_engine(ticks_per_day=2)
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    await engine.run_tick()
    assert memory.stored_summaries == []  # aún no es el final del día

    await engine.run_tick()
    assert len(memory.stored_summaries) == 1
    agent_id, day, summary = memory.stored_summaries[0]
    assert agent_id == "agent-1"
    assert day == 1
    assert "tick 1" in summary
    assert "tick 2" in summary


async def test_sleep_cycle_clears_daily_log_after_persisting() -> None:
    engine, memory, _ = _make_engine(ticks_per_day=1)
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    await engine.run_tick()
    await engine.run_tick()

    assert len(memory.stored_summaries) == 2  # un resumen por día, sin arrastrar el anterior
    assert "tick 1" not in memory.stored_summaries[1][2]


async def test_adjust_trust_updates_the_agents_trust_links() -> None:
    engine, _, _ = _make_engine()
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    engine.adjust_trust("agent-1", "agent-2", -0.3)
    engine.adjust_trust("agent-1", "agent-2", -0.3)

    assert engine.agent_snapshot("agent-1").trust_links["agent-2"] == pytest.approx(-0.6)


async def test_adjust_trust_clamps_to_valid_range() -> None:
    engine, _, _ = _make_engine()
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    for _ in range(10):
        engine.adjust_trust("agent-1", "agent-2", -0.3)

    assert engine.agent_snapshot("agent-1").trust_links["agent-2"] == -1.0


async def test_adjust_trust_on_unknown_agent_is_a_no_op() -> None:
    engine, _, _ = _make_engine()

    engine.adjust_trust("ghost", "agent-2", -0.3)  # no debe lanzar


async def test_inflation_rate_is_zero_before_a_full_day_has_elapsed() -> None:
    engine, _, _ = _make_engine(ticks_per_day=3)
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    event = await engine.run_tick()

    assert event.indicators.inflation_rate == 0.0


async def test_inflation_rate_reflects_energy_price_drift_after_one_day() -> None:
    engine, _, _ = _make_engine(ticks_per_day=2)
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    for _ in range(3):
        event = await engine.run_tick()

    assert event.indicators.inflation_rate != 0.0


class _SleepOnceLLM(FakeLLM):
    """Devuelve `sleep` en la primera invocación e `idle` en las siguientes."""

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    async def generate_action(self, system_prompt: str, context: PerceivedContext) -> AgentAction:
        self.calls += 1
        action_type = ActionType.SLEEP if self.calls == 1 else ActionType.IDLE
        return AgentAction(action_type=action_type, reasoning="cycle test")


async def test_sleeping_agent_wakes_up_on_the_next_tick() -> None:
    engine, _, _ = _make_engine(llm=_SleepOnceLLM())
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    await engine.run_tick()
    assert engine.agent_snapshot("agent-1").status is AgentStatus.SLEEPING

    await engine.run_tick()
    assert engine.agent_snapshot("agent-1").status is AgentStatus.ALIVE


async def test_run_tick_survives_an_economically_invalid_action() -> None:
    # El agente intenta transferir más SimCoin del que tiene: la acción se
    # descarta, pero el tick global continúa y el coste pasivo se cobra igual.
    overdraft = AgentAction(
        action_type=ActionType.TRANSFER,
        reasoning="spending beyond my means",
        payload={"to_agent": "agent-2", "amount": "9999"},
    )
    engine, _, _ = _make_engine(llm=FakeLLM(overdraft))
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")
    engine.register_agent(_make_agent_state("agent-2"), system_prompt="be productive")

    event = await engine.run_tick()

    assert event.tick == 1
    assert engine.agent_snapshot("agent-1").balance == Decimal("49.0")
    assert engine.agent_snapshot("agent-2").balance == Decimal("49.0")


class _ExplodingJudge:
    """Doble del Agente Juez cuya revisión siempre falla."""

    def __init__(self) -> None:
        self.calls = 0

    async def review_disputed_contracts(self, tick: int) -> list[object]:
        self.calls += 1
        raise RuntimeError("judge model returned garbage")


async def test_tick_loop_keeps_running_when_the_judge_fails() -> None:
    engine, _, _ = _make_engine()
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")
    judge = _ExplodingJudge()
    ledger_store = FakeLedgerStore()

    task = asyncio.create_task(
        _tick_loop(engine, judge, ledger_store, ticks_per_day=1_000_000, interval_seconds=0.001)  # type: ignore[arg-type]
    )

    async def _wait_for_ticks() -> None:
        while engine.current_tick < 3:
            await asyncio.sleep(0.001)

    try:
        await asyncio.wait_for(_wait_for_ticks(), timeout=5.0)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    # El reloj siguió avanzando pese a que cada revisión del Juez explotó.
    assert engine.current_tick >= 3
    assert judge.calls >= 1


async def test_transactions_per_minute_matches_real_tick_cadence() -> None:
    # Con un coste pasivo por tick y un intervalo de 5s, el ritmo esperado es
    # de 60/5 = 12 transacciones por minuto con un único agente registrado.
    engine, _, _ = _make_engine(tick_interval_seconds=5.0)
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    event = await engine.run_tick()

    assert event.indicators.transactions_per_minute == pytest.approx(12.0)


async def test_pending_contract_stays_pending_within_the_grace_period() -> None:
    engine, _, contracts = _make_engine(ticks_per_day=2)
    contract = contracts.create_contract(
        "agent-1", "agent-2", "deliver 10 vector packs", Decimal("10.0"), tick=0
    )

    await engine.run_tick()  # tick 1: 1 - 0 = 1 < 2, aún dentro del plazo

    assert contracts.get(contract.contract_id).status.value == "pending"


async def test_overdue_pending_contract_is_auto_escalated_to_disputed() -> None:
    # Ningún agente elige FILE_DISPUTE, pero el contrato lleva más de un día
    # simulado en PENDING: el sistema lo escala solo para que llegue al Juez.
    engine, _, contracts = _make_engine(ticks_per_day=2)
    contract = contracts.create_contract(
        "agent-1", "agent-2", "deliver 10 vector packs", Decimal("10.0"), tick=0
    )

    await engine.run_tick()  # tick 1
    await engine.run_tick()  # tick 2: 2 - 0 = 2 >= 2, se escala

    assert contracts.get(contract.contract_id).status.value == "disputed"


async def test_already_resolved_contracts_are_not_touched_by_expiration() -> None:
    engine, _, contracts = _make_engine(ticks_per_day=1)
    contract = contracts.create_contract(
        "agent-1", "agent-2", "deliver 10 vector packs", Decimal("10.0"), tick=0
    )
    contracts.mark_fulfilled(contract.contract_id)

    await engine.run_tick()
    await engine.run_tick()

    assert contracts.get(contract.contract_id).status.value == "fulfilled"


async def test_apply_energy_shock_scales_the_current_price_immediately() -> None:
    engine, _, _ = _make_engine()
    price_before = engine.current_energy_price

    new_price = engine.apply_energy_shock(Decimal("2.0"))

    assert new_price == price_before * Decimal("2.0")
    assert engine.current_energy_price == new_price


async def test_apply_energy_shock_persists_into_the_next_ticks_price() -> None:
    engine, _, _ = _make_engine()
    engine.apply_energy_shock(Decimal("3.0"))

    await engine.run_tick()

    # El shock desplaza el precio BASE, así que se refleja en el próximo tick
    # calculado (no solo en el instante en que se aplicó la intervención).
    assert engine.current_energy_price > Decimal("2.5")


async def test_apply_energy_shock_rejects_non_positive_factor() -> None:
    engine, _, _ = _make_engine()

    with pytest.raises(ValueError, match="positive"):
        engine.apply_energy_shock(Decimal("0"))
