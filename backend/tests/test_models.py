import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from enclave.models import (
    AgentState,
    AgentStatus,
    AssetType,
    MarketOffer,
    Personality,
    Position,
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
