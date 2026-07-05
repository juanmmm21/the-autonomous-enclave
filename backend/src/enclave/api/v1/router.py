"""Endpoints REST versionados de la API. Capa delgada: no duplica lógica de
negocio, solo la expone sobre el `TickEngine` ya orquestado en `main.py`."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from enclave.api.deps import get_tick_engine
from enclave.models import AgentState
from enclave.services.tick_engine import TickEngine

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/agents", response_model=list[AgentState])
async def list_agents(engine: TickEngine = Depends(get_tick_engine)) -> list[AgentState]:
    return [engine.agent_snapshot(agent_id) for agent_id in engine.all_agent_ids()]


@router.get("/agents/{agent_id}", response_model=AgentState)
async def get_agent(agent_id: str, engine: TickEngine = Depends(get_tick_engine)) -> AgentState:
    try:
        return engine.agent_snapshot(agent_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"agent {agent_id} not found") from exc


@router.get("/tick", response_model=dict[str, int])
async def current_tick(engine: TickEngine = Depends(get_tick_engine)) -> dict[str, int]:
    return {"tick": engine.current_tick}
