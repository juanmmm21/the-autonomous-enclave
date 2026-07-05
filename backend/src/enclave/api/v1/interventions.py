"""Consola de Intervención Divina: acciones directas del 'Dios Observador'
sobre la economía y la infraestructura de la simulación."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from enclave.api.deps import get_tick_engine
from enclave.models import AgentState
from enclave.services.tick_engine import TickEngine

router = APIRouter()


class DevaluationRequest(BaseModel):
    factor: Decimal = Field(gt=0, le=1, description="1.0 = sin cambio, 0.5 = devaluación del 50%")


class SubsidyRequest(BaseModel):
    agent_id: str
    amount: Decimal = Field(gt=0)


class InferenceQuotaRequest(BaseModel):
    agent_id: str
    quota: int = Field(ge=0)


class EnergyShockRequest(BaseModel):
    factor: Decimal = Field(gt=0, description=">1 simula escasez, <1 simula abundancia energética")


@router.post("/interventions/devalue")
async def devalue_currency(
    body: DevaluationRequest, engine: TickEngine = Depends(get_tick_engine)
) -> dict[str, str]:
    engine.bank.devalue_currency(body.factor)
    engine.sync_balances_from_bank()
    return {"status": "applied", "factor": str(body.factor)}


@router.post("/interventions/subsidize", response_model=AgentState)
async def subsidize_agent(
    body: SubsidyRequest, engine: TickEngine = Depends(get_tick_engine)
) -> AgentState:
    # Se valida contra el registro de ciudadanos, no contra el banco: el tesoro
    # tiene cuenta bancaria pero no es un agente subvencionable.
    if body.agent_id not in engine.all_agent_ids():
        raise HTTPException(status_code=404, detail=f"agent {body.agent_id} not found")

    engine.bank.print_subsidy(body.agent_id, body.amount, engine.current_tick)
    engine.sync_balances_from_bank()
    return engine.agent_snapshot(body.agent_id)


@router.post("/interventions/blackout", response_model=AgentState)
async def blackout_agent(
    body: InferenceQuotaRequest, engine: TickEngine = Depends(get_tick_engine)
) -> AgentState:
    try:
        return engine.set_inference_quota(body.agent_id, body.quota)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"agent {body.agent_id} not found") from exc


@router.post("/interventions/energy_shock")
async def energy_shock(
    body: EnergyShockRequest, engine: TickEngine = Depends(get_tick_engine)
) -> dict[str, str]:
    new_price = engine.apply_energy_shock(body.factor)
    return {"status": "applied", "factor": str(body.factor), "energy_price": str(new_price)}
