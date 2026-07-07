"""Creación de ciudadanos en caliente desde la web: registra un nuevo agente en
el `TickEngine` sin reiniciar la simulación y difunde de inmediato un
`TickEvent` actualizado para que aparezca en el mapa sin esperar al próximo
tick natural."""

from __future__ import annotations

import re
import unicodedata
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from enclave.api.deps import get_telemetry_hub, get_tick_engine
from enclave.api.v1.websocket import TelemetryHub
from enclave.models import AgentState, Personality, Position
from enclave.seed import (
    DEFAULT_INFERENCE_QUOTA,
    DEFAULT_SPAWN_POSITION,
    DEFAULT_STARTING_BALANCE,
    build_system_prompt,
    describe_traits,
)
from enclave.services.tick_engine import TickEngine

router = APIRouter()


class CreateCitizenRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)
    personality: list[Personality] = Field(min_length=1)
    starting_balance: Decimal = Field(default=DEFAULT_STARTING_BALANCE, gt=0)
    position: Position | None = None

    @field_validator("display_name")
    @classmethod
    def _strip_display_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("display_name must not be blank")
        return stripped

    @field_validator("personality")
    @classmethod
    def _dedupe_personality(cls, value: list[Personality]) -> list[Personality]:
        # Preserva el orden de la primera aparición: duplicar un rasgo no debe
        # duplicar su fragmento en el system prompt.
        return list(dict.fromkeys(value))


def _slugify(display_name: str) -> str:
    """Slug ASCII en minúsculas del nombre (Á í → a i, espacios → guiones)."""
    normalized = unicodedata.normalize("NFKD", display_name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return slug


@router.post("/citizens", response_model=AgentState, status_code=201)
async def create_citizen(
    body: CreateCitizenRequest,
    engine: TickEngine = Depends(get_tick_engine),
    hub: TelemetryHub = Depends(get_telemetry_hub),
) -> AgentState:
    slug = _slugify(body.display_name)
    if not slug:
        raise HTTPException(
            status_code=422,
            detail="display_name must contain at least one alphanumeric character",
        )

    # El sufijo aleatorio hace la colisión improbable incluso con nombres
    # repetidos, pero un id ya registrado se rechaza explícitamente: pisar el
    # estado de un ciudadano vivo en silencio sería corrupción de datos.
    agent_id = f"agent-{slug}-{uuid.uuid4().hex[:6]}"
    if agent_id in engine.all_agent_ids():
        raise HTTPException(status_code=409, detail=f"agent id {agent_id} already exists")

    agent_state = AgentState(
        agent_id=agent_id,
        display_name=body.display_name,
        personality=body.personality,
        balance=body.starting_balance,
        inference_quota=DEFAULT_INFERENCE_QUOTA,
        position=body.position or DEFAULT_SPAWN_POSITION,
    )
    system_prompt = build_system_prompt(body.display_name, describe_traits(body.personality))
    engine.register_agent(agent_state, system_prompt)

    # Difusión inmediata: el ciudadano aparece en el mapa en cuanto se crea,
    # sin esperar los ~5s del próximo tick.
    await hub.broadcast(await engine.snapshot_event())
    return engine.agent_snapshot(agent_id)
