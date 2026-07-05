from decimal import Decimal

from conftest import FakeBroker, FakeLLM, FakeMemoryStore

from enclave.seed import INITIAL_CITIZENS, seed_initial_citizens
from enclave.services.agent_runtime import AgentRuntime
from enclave.services.contracts import ContractRegistry
from enclave.services.economy import CentralBank
from enclave.services.tick_engine import TickEngine


def _make_engine() -> TickEngine:
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    memory_store = FakeMemoryStore()
    runtime = AgentRuntime(FakeLLM(), FakeBroker(), bank, ContractRegistry(), memory_store)
    return TickEngine(runtime, bank, memory_store, energy_price=Decimal("1.0"))


def test_seed_registers_every_blueprint() -> None:
    engine = _make_engine()

    seed_initial_citizens(engine)

    registered_ids = set(engine.all_agent_ids())
    expected_ids = {blueprint.agent_id for blueprint in INITIAL_CITIZENS}
    assert registered_ids == expected_ids


def test_seeded_agents_have_open_bank_accounts_matching_starting_balance() -> None:
    engine = _make_engine()

    seed_initial_citizens(engine)

    for blueprint in INITIAL_CITIZENS:
        assert engine.bank.get_balance(blueprint.agent_id) == blueprint.starting_balance
        assert engine.agent_snapshot(blueprint.agent_id).balance == blueprint.starting_balance


def test_every_blueprint_has_a_non_empty_system_prompt() -> None:
    for blueprint in INITIAL_CITIZENS:
        assert len(blueprint.system_prompt) > 20
        assert blueprint.display_name in blueprint.system_prompt
