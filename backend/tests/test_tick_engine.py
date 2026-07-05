from decimal import Decimal

import pytest
from conftest import FakeBroker, FakeLLM, FakeMemoryStore

from enclave.models import AgentState, Personality, Position
from enclave.services.agent_runtime import AgentRuntime
from enclave.services.contracts import ContractRegistry
from enclave.services.economy import CentralBank
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
) -> tuple[TickEngine, FakeMemoryStore]:
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    memory = memory_store or FakeMemoryStore()
    runtime = AgentRuntime(FakeLLM(), broker or FakeBroker(), bank, ContractRegistry(), memory)
    engine = TickEngine(
        runtime,
        bank,
        memory,
        energy_price=Decimal("1.0"),
        ticks_per_day=ticks_per_day,
        tick_interval_seconds=tick_interval_seconds,
    )
    return engine, memory


async def test_run_tick_charges_passive_cost_to_registered_agents() -> None:
    engine, _ = _make_engine()
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    await engine.run_tick()

    assert engine.agent_snapshot("agent-1").balance == Decimal("49.0")


async def test_run_tick_survives_infrastructure_failure_in_perceive() -> None:
    engine, _ = _make_engine(broker=_BrokenBroker())
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    event = await engine.run_tick()

    # El agente sigue existiendo y paga su coste pasivo pese al fallo de Redis.
    assert engine.agent_snapshot("agent-1").balance == Decimal("49.0")
    assert event.tick == 1


async def test_sleep_cycle_persists_daily_summary_at_day_boundary() -> None:
    engine, memory = _make_engine(ticks_per_day=2)
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
    engine, memory = _make_engine(ticks_per_day=1)
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    await engine.run_tick()
    await engine.run_tick()

    assert len(memory.stored_summaries) == 2  # un resumen por día, sin arrastrar el anterior
    assert "tick 1" not in memory.stored_summaries[1][2]


async def test_adjust_trust_updates_the_agents_trust_links() -> None:
    engine, _ = _make_engine()
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    engine.adjust_trust("agent-1", "agent-2", -0.3)
    engine.adjust_trust("agent-1", "agent-2", -0.3)

    assert engine.agent_snapshot("agent-1").trust_links["agent-2"] == pytest.approx(-0.6)


async def test_adjust_trust_clamps_to_valid_range() -> None:
    engine, _ = _make_engine()
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    for _ in range(10):
        engine.adjust_trust("agent-1", "agent-2", -0.3)

    assert engine.agent_snapshot("agent-1").trust_links["agent-2"] == -1.0


async def test_adjust_trust_on_unknown_agent_is_a_no_op() -> None:
    engine, _ = _make_engine()

    engine.adjust_trust("ghost", "agent-2", -0.3)  # no debe lanzar


async def test_inflation_rate_is_zero_before_a_full_day_has_elapsed() -> None:
    engine, _ = _make_engine(ticks_per_day=3)
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    event = await engine.run_tick()

    assert event.indicators.inflation_rate == 0.0


async def test_inflation_rate_reflects_energy_price_drift_after_one_day() -> None:
    engine, _ = _make_engine(ticks_per_day=2)
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    for _ in range(3):
        event = await engine.run_tick()

    assert event.indicators.inflation_rate != 0.0


async def test_transactions_per_minute_matches_real_tick_cadence() -> None:
    # Con un coste pasivo por tick y un intervalo de 5s, el ritmo esperado es
    # de 60/5 = 12 transacciones por minuto con un único agente registrado.
    engine, _ = _make_engine(tick_interval_seconds=5.0)
    engine.register_agent(_make_agent_state("agent-1"), system_prompt="be productive")

    event = await engine.run_tick()

    assert event.indicators.transactions_per_minute == pytest.approx(12.0)
