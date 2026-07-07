import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from enclave.models import (
    GRID_HEIGHT,
    GRID_WIDTH,
    ActionType,
    AgentAction,
    AgentState,
    AgentStatus,
    AssetType,
    EconomicIndicators,
    MarketOffer,
    Personality,
    Position,
    TickEvent,
)


def _make_agent_state(**overrides: object) -> AgentState:
    defaults: dict[str, object] = {
        "agent_id": "agent-1",
        "display_name": "Ada",
        "personality": [Personality.AMBITIOUS],
        "balance": Decimal("100.0"),
        "inference_quota": 3,
        "position": Position(x=0, y=0),
    }
    defaults.update(overrides)
    return AgentState.model_validate(defaults)


def test_agent_state_requires_at_least_one_personality_trait() -> None:
    with pytest.raises(ValidationError):
        _make_agent_state(personality=[])


def test_agent_state_defaults_to_alive_status() -> None:
    agent = _make_agent_state()

    assert agent.status == AgentStatus.ALIVE
    assert agent.inventory == {}
    assert agent.trust_links == {}


def test_decimal_balance_serializes_as_string_in_json() -> None:
    agent = _make_agent_state(balance=Decimal("123.45"))

    payload = json.loads(agent.model_dump_json())

    assert payload["balance"] == "123.45"
    assert isinstance(payload["balance"], str)


def test_position_accepts_coordinates_within_grid_bounds() -> None:
    position = Position(x=GRID_WIDTH - 1, y=GRID_HEIGHT - 1)

    assert position.x == GRID_WIDTH - 1
    assert position.y == GRID_HEIGHT - 1


def test_position_rejects_coordinates_outside_grid_bounds() -> None:
    with pytest.raises(ValidationError):
        Position(x=GRID_WIDTH, y=0)
    with pytest.raises(ValidationError):
        Position(x=0, y=GRID_HEIGHT)


def test_market_offer_rejects_non_positive_quantity() -> None:
    with pytest.raises(ValidationError):
        MarketOffer(
            offer_id="offer-1",
            seller_id="agent-1",
            asset_type=AssetType.INFERENCE_QUOTA,
            quantity=0,
            unit_price=Decimal("5.0"),
            created_at_tick=1,
        )


def test_market_offer_unit_price_serializes_as_string() -> None:
    offer = MarketOffer(
        offer_id="offer-1",
        seller_id="agent-1",
        asset_type=AssetType.VECTOR_PACK,
        quantity=2,
        unit_price=Decimal("7.5"),
        created_at_tick=1,
    )

    payload = json.loads(offer.model_dump_json())

    assert payload["unit_price"] == "7.5"


def test_agent_action_coerces_explicit_null_payload_to_empty_dict() -> None:
    # llama3.2 a veces devuelve "payload": null en vez de omitir la clave.
    action = AgentAction.model_validate(
        {"action_type": "sleep", "reasoning": "necesito descansar", "payload": None}
    )

    assert action.payload == {}


def test_agent_action_default_payload_is_empty_dict_when_key_absent() -> None:
    action = AgentAction(action_type=ActionType.IDLE, reasoning="nada que hacer")

    assert action.payload == {}


def _make_tick_event(**overrides: object) -> TickEvent:
    defaults: dict[str, object] = {
        "tick": 1,
        "timestamp": datetime.now(UTC),
        "agents": [],
        "indicators": EconomicIndicators(
            gini_index=0.0, inflation_rate=0.0, virtual_gdp=0.0, transactions_per_minute=0.0
        ),
        "ticks_per_day": 10,
    }
    defaults.update(overrides)
    return TickEvent.model_validate(defaults)


def test_tick_event_activity_feed_fields_default_to_empty() -> None:
    event = _make_tick_event()

    assert event.market_offers == []
    assert event.open_contracts == []
    assert event.recent_rulings == []


def test_tick_event_rejects_a_non_positive_ticks_per_day() -> None:
    with pytest.raises(ValidationError):
        _make_tick_event(ticks_per_day=0)


def test_tick_event_serializes_nested_money_amounts_as_strings() -> None:
    ruling = {
        "ruling_id": "ruling-1",
        "contract_id": "contract-1",
        "at_fault_agent": "agent-1",
        "verdict": "breached terms",
        "penalty": Decimal("12.5"),
        "ruled_at_tick": 3,
    }
    event = _make_tick_event(recent_rulings=[ruling])

    payload = json.loads(event.model_dump_json())

    assert payload["recent_rulings"][0]["penalty"] == "12.5"
