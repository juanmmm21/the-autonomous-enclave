"""Tests del endpoint de creación de ciudadanos en caliente (`POST /citizens`).

Se monta una app FastAPI mínima con el router y un `TickEngine` real sobre los
dobles en memoria de conftest, sin lifespan (no hay Redis/Postgres en tests).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from conftest import FakeBroker, FakeLLM, FakeMemoryStore
from fastapi import FastAPI
from fastapi.testclient import TestClient

from enclave.api.v1.citizens import router as citizens_router
from enclave.api.v1.websocket import TelemetryHub
from enclave.models import GRID_HEIGHT, GRID_WIDTH, TickEvent
from enclave.seed import DEFAULT_SPAWN_POSITION, DEFAULT_STARTING_BALANCE
from enclave.services.agent_runtime import AgentRuntime
from enclave.services.contracts import ContractRegistry
from enclave.services.economy import CentralBank
from enclave.services.inference_market import InferenceQuotaLedger
from enclave.services.tick_engine import TickEngine


def _make_test_app() -> tuple[TestClient, TickEngine, list[TickEvent]]:
    bank = CentralBank(passive_tick_cost=Decimal("1.0"))
    quotas = InferenceQuotaLedger()
    contracts = ContractRegistry()
    memory = FakeMemoryStore()
    broker = FakeBroker()
    runtime = AgentRuntime(FakeLLM(), broker, bank, contracts, memory, quotas)
    engine = TickEngine(
        runtime, bank, memory, quotas, contracts, broker, energy_price=Decimal("1.0")
    )

    broadcasts: list[TickEvent] = []

    class _RecordingHub(TelemetryHub):
        async def broadcast(self, event: TickEvent) -> None:
            broadcasts.append(event)

    app = FastAPI()
    app.include_router(citizens_router, prefix="/api/v1")
    app.state.tick_engine = engine
    app.state.telemetry_hub = _RecordingHub()
    return TestClient(app), engine, broadcasts


def test_create_citizen_registers_the_agent_with_defaults() -> None:
    client, engine, _ = _make_test_app()

    response = client.post(
        "/api/v1/citizens",
        json={"display_name": "Rosa", "personality": ["cooperative", "ambitious"]},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["display_name"] == "Rosa"
    assert payload["personality"] == ["cooperative", "ambitious"]
    assert payload["balance"] == str(DEFAULT_STARTING_BALANCE)
    assert payload["position"] == {"x": DEFAULT_SPAWN_POSITION.x, "y": DEFAULT_SPAWN_POSITION.y}
    assert payload["agent_id"].startswith("agent-rosa-")
    assert payload["agent_id"] in engine.all_agent_ids()
    assert engine.bank.get_balance(payload["agent_id"]) == DEFAULT_STARTING_BALANCE


def test_create_citizen_broadcasts_an_immediate_tick_event() -> None:
    client, _, broadcasts = _make_test_app()

    response = client.post(
        "/api/v1/citizens", json={"display_name": "Rosa", "personality": ["cautious"]}
    )

    assert response.status_code == 201
    assert len(broadcasts) == 1
    broadcast_ids = [agent.agent_id for agent in broadcasts[0].agents]
    assert response.json()["agent_id"] in broadcast_ids


def test_create_citizen_accepts_explicit_balance_and_position() -> None:
    client, _, _ = _make_test_app()

    response = client.post(
        "/api/v1/citizens",
        json={
            "display_name": "Vera",
            "personality": ["altruistic"],
            "starting_balance": "250.5",
            "position": {"x": 3, "y": 7},
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["balance"] == "250.5"
    assert payload["position"] == {"x": 3, "y": 7}


def test_create_citizen_slugifies_accents_and_spaces_in_the_agent_id() -> None:
    client, _, _ = _make_test_app()

    response = client.post(
        "/api/v1/citizens",
        json={"display_name": "María José", "personality": ["cooperative"]},
    )

    assert response.status_code == 201
    assert response.json()["agent_id"].startswith("agent-maria-jose-")


def test_create_citizen_rejects_blank_display_name() -> None:
    client, _, _ = _make_test_app()

    response = client.post(
        "/api/v1/citizens", json={"display_name": "   ", "personality": ["cautious"]}
    )

    assert response.status_code == 422


def test_create_citizen_rejects_a_name_without_alphanumeric_characters() -> None:
    client, _, _ = _make_test_app()

    response = client.post(
        "/api/v1/citizens", json={"display_name": "!!!", "personality": ["cautious"]}
    )

    assert response.status_code == 422


def test_create_citizen_rejects_empty_personality() -> None:
    client, _, _ = _make_test_app()

    response = client.post("/api/v1/citizens", json={"display_name": "Rosa", "personality": []})

    assert response.status_code == 422


def test_create_citizen_rejects_an_unknown_personality_trait() -> None:
    client, _, _ = _make_test_app()

    response = client.post(
        "/api/v1/citizens", json={"display_name": "Rosa", "personality": ["heroic"]}
    )

    assert response.status_code == 422


def test_create_citizen_rejects_non_positive_balance() -> None:
    client, _, _ = _make_test_app()

    response = client.post(
        "/api/v1/citizens",
        json={"display_name": "Rosa", "personality": ["cautious"], "starting_balance": "0"},
    )

    assert response.status_code == 422


def test_create_citizen_rejects_out_of_grid_position() -> None:
    client, _, _ = _make_test_app()

    response = client.post(
        "/api/v1/citizens",
        json={
            "display_name": "Rosa",
            "personality": ["cautious"],
            "position": {"x": GRID_WIDTH, "y": GRID_HEIGHT},
        },
    )

    assert response.status_code == 422


def test_create_citizen_rejects_an_id_collision_with_409(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine, _ = _make_test_app()
    first = client.post(
        "/api/v1/citizens", json={"display_name": "Rosa", "personality": ["cautious"]}
    )
    taken_id = first.json()["agent_id"]

    # Se fuerza la colisión fijando el sufijo que devuelve uuid4: es aleatorio,
    # así que es la única forma determinista de reproducir un id ya registrado.
    class _FixedUUID:
        hex = taken_id.removeprefix("agent-rosa-")

    monkeypatch.setattr("enclave.api.v1.citizens.uuid.uuid4", lambda: _FixedUUID())

    response = client.post(
        "/api/v1/citizens", json={"display_name": "Rosa", "personality": ["cautious"]}
    )

    assert response.status_code == 409
    assert engine.all_agent_ids().count(taken_id) == 1


def test_duplicate_personality_traits_are_deduped() -> None:
    client, _, _ = _make_test_app()

    response = client.post(
        "/api/v1/citizens",
        json={"display_name": "Rosa", "personality": ["cautious", "cautious", "ambitious"]},
    )

    assert response.status_code == 201
    assert response.json()["personality"] == ["cautious", "ambitious"]
