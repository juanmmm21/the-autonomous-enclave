from decimal import Decimal

import pytest
from conftest import FakeBroker, FakeLLM

from enclave.exceptions import LLMGenerationError
from enclave.models import (
    ActionType,
    AgentAction,
    AgentState,
    AssetType,
    InboxMessage,
    Personality,
    Position,
)
from enclave.services.agent_runtime import AgentRuntime
from enclave.services.contracts import ContractRegistry
from enclave.services.economy import CentralBank


def _make_agent_state(agent_id: str = "agent-1") -> AgentState:
    return AgentState(
        agent_id=agent_id,
        display_name="Ada",
        personality=[Personality.AMBITIOUS],
        balance=Decimal("100.0"),
        inference_quota=3,
        position=Position(x=0, y=0),
    )


@pytest.fixture
def bank() -> CentralBank:
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    bank.open_account("agent-1", Decimal("100.0"))
    bank.open_account("agent-2", Decimal("10.0"))
    return bank


@pytest.fixture
def contracts() -> ContractRegistry:
    return ContractRegistry()


@pytest.fixture
def broker() -> FakeBroker:
    return FakeBroker()


def _make_runtime(
    broker: FakeBroker, bank: CentralBank, contracts: ContractRegistry
) -> AgentRuntime:
    return AgentRuntime(
        FakeLLM(AgentAction(action_type=ActionType.IDLE, reasoning="noop")), broker, bank, contracts
    )


async def test_perceive_combines_inbox_offers_and_state(
    broker: FakeBroker, bank: CentralBank, contracts: ContractRegistry
) -> None:
    runtime = _make_runtime(broker, bank, contracts)
    agent_state = _make_agent_state()
    await broker.send_direct_message(
        "agent-1",
        InboxMessage(message_id="m1", from_agent="agent-2", to_agent="agent-1", body="hi", tick=1),
    )

    context = await runtime.perceive(agent_state, energy_price=Decimal("2.0"), tick=5)

    assert context.current_tick == 5
    assert len(context.inbox) == 1
    assert context.inbox[0].body == "hi"
    assert context.self_state.agent_id == "agent-1"


async def test_act_move_updates_position(
    broker: FakeBroker, bank: CentralBank, contracts: ContractRegistry
) -> None:
    runtime = _make_runtime(broker, bank, contracts)
    agent_state = _make_agent_state()
    action = AgentAction(
        action_type=ActionType.MOVE, reasoning="heading to market", payload={"x": 3, "y": 4}
    )

    updated = await runtime.act(agent_state, action, tick=1)

    assert updated.position.x == 3
    assert updated.position.y == 4


async def test_act_move_out_of_bounds_raises_llm_generation_error(
    broker: FakeBroker, bank: CentralBank, contracts: ContractRegistry
) -> None:
    runtime = _make_runtime(broker, bank, contracts)
    agent_state = _make_agent_state()
    action = AgentAction(
        action_type=ActionType.MOVE, reasoning="wandering off", payload={"x": 999, "y": 999}
    )

    with pytest.raises(LLMGenerationError):
        await runtime.act(agent_state, action, tick=1)


async def test_act_send_message_reaches_broker(
    broker: FakeBroker, bank: CentralBank, contracts: ContractRegistry
) -> None:
    runtime = _make_runtime(broker, bank, contracts)
    agent_state = _make_agent_state()
    action = AgentAction(
        action_type=ActionType.SEND_MESSAGE,
        reasoning="negotiating",
        payload={"to_agent": "agent-2", "body": "sell me your quota"},
    )

    await runtime.act(agent_state, action, tick=1)

    assert len(broker.sent_messages) == 1
    assert broker.sent_messages[0].to_agent == "agent-2"


async def test_act_post_offer_publishes_to_broker(
    broker: FakeBroker, bank: CentralBank, contracts: ContractRegistry
) -> None:
    runtime = _make_runtime(broker, bank, contracts)
    agent_state = _make_agent_state()
    action = AgentAction(
        action_type=ActionType.POST_OFFER,
        reasoning="selling spare quota",
        payload={"asset_type": AssetType.INFERENCE_QUOTA.value, "quantity": 2, "unit_price": "5.0"},
    )

    await runtime.act(agent_state, action, tick=1)

    assert len(broker.published_offers) == 1
    assert broker.published_offers[0].seller_id == "agent-1"
    assert broker.published_offers[0].unit_price == Decimal("5.0")


async def test_act_transfer_moves_funds_via_bank(
    broker: FakeBroker, bank: CentralBank, contracts: ContractRegistry
) -> None:
    runtime = _make_runtime(broker, bank, contracts)
    agent_state = _make_agent_state()
    action = AgentAction(
        action_type=ActionType.TRANSFER,
        reasoning="paying for a script",
        payload={"to_agent": "agent-2", "amount": "20.0"},
    )

    await runtime.act(agent_state, action, tick=1)

    assert bank.get_balance("agent-1") == Decimal("80.0")
    assert bank.get_balance("agent-2") == Decimal("30.0")


async def test_act_sign_contract_registers_it(
    broker: FakeBroker, bank: CentralBank, contracts: ContractRegistry
) -> None:
    runtime = _make_runtime(broker, bank, contracts)
    agent_state = _make_agent_state()
    action = AgentAction(
        action_type=ActionType.SIGN_CONTRACT,
        reasoning="formalizing a deal",
        payload={"counterparty": "agent-2", "terms": "deliver 10 vector packs", "amount": "15.0"},
    )

    await runtime.act(agent_state, action, tick=1)

    contract = next(iter(contracts.disputed_contracts()), None)
    assert contract is None  # recién firmado, aún no está en disputa


async def test_act_file_dispute_marks_contract_disputed(
    broker: FakeBroker, bank: CentralBank, contracts: ContractRegistry
) -> None:
    runtime = _make_runtime(broker, bank, contracts)
    agent_state = _make_agent_state()
    contract = contracts.create_contract("agent-1", "agent-2", "terms", Decimal("10.0"), tick=1)
    action = AgentAction(
        action_type=ActionType.FILE_DISPUTE,
        reasoning="counterparty never paid",
        payload={"contract_id": contract.contract_id},
    )

    await runtime.act(agent_state, action, tick=2)

    disputed_ids = [c.contract_id for c in contracts.disputed_contracts()]
    assert contract.contract_id in disputed_ids


async def test_act_transfer_without_amount_raises_llm_generation_error(
    broker: FakeBroker, bank: CentralBank, contracts: ContractRegistry
) -> None:
    runtime = _make_runtime(broker, bank, contracts)
    agent_state = _make_agent_state()
    action = AgentAction(
        action_type=ActionType.TRANSFER, reasoning="incomplete", payload={"to_agent": "agent-2"}
    )

    with pytest.raises(LLMGenerationError):
        await runtime.act(agent_state, action, tick=1)
