"""Tipos de dominio de The Autonomous Enclave.

Todas las magnitudes financieras usan `Decimal` internamente y se serializan
como `str` en JSON (ver `MoneyModel`) para evitar errores de redondeo binario
en balances de SimCoin.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_serializer

SimCoin = Annotated[Decimal, Field(description="Monto expresado en SimCoin")]


class MoneyModel(BaseModel):
    """Base para modelos con campos `Decimal`: se serializan como string en JSON."""

    model_config = ConfigDict(frozen=False)

    @field_serializer("*", when_used="json", check_fields=False)
    def _serialize_decimal(self, value: object) -> object:
        if isinstance(value, Decimal):
            return str(value)
        return value


class Personality(StrEnum):
    AMBITIOUS = "ambitious"
    CAUTIOUS = "cautious"
    COOPERATIVE = "cooperative"
    ALTRUISTIC = "altruistic"
    MACHIAVELLIAN = "machiavellian"


class AgentStatus(StrEnum):
    ALIVE = "alive"
    SLEEPING = "sleeping"
    BANKRUPT = "bankrupt"
    TERMINATED = "terminated"


class AssetType(StrEnum):
    """Los cinco activos que circulan en la economía de silicio (ver docs/vision.md)."""

    INFERENCE_QUOTA = "inference_quota"
    VECTOR_PACK = "vector_pack"
    ALPHA_SIGNAL = "alpha_signal"
    CODE_SCRIPT = "code_script"
    FINANCIAL_DERIVATIVE = "financial_derivative"


class ContractStatus(StrEnum):
    PENDING = "pending"
    FULFILLED = "fulfilled"
    DISPUTED = "disputed"
    BREACHED = "breached"


class ActionType(StrEnum):
    """Único vocabulario de salida que el LLM puede producir en la fase Act."""

    MOVE = "move"
    SEND_MESSAGE = "send_message"
    POST_OFFER = "post_offer"
    ACCEPT_OFFER = "accept_offer"
    SIGN_CONTRACT = "sign_contract"
    FILE_DISPUTE = "file_dispute"
    TRANSFER = "transfer"
    SLEEP = "sleep"
    IDLE = "idle"


# Debe coincidir con GRID_WIDTH/GRID_HEIGHT en frontend/src/components/phaser/MainScene.ts,
# que renderiza el mapa sobre el que se mueven estas coordenadas.
GRID_WIDTH = 20
GRID_HEIGHT = 15


class Position(BaseModel):
    x: int = Field(ge=0, lt=GRID_WIDTH)
    y: int = Field(ge=0, lt=GRID_HEIGHT)


class AgentState(MoneyModel):
    agent_id: str
    display_name: str
    personality: list[Personality] = Field(min_length=1)
    balance: SimCoin
    inventory: dict[AssetType, int] = Field(default_factory=dict)
    inference_quota: int = Field(ge=0, description="Slots de inferencia disponibles este tick")
    position: Position
    status: AgentStatus = AgentStatus.ALIVE
    trust_links: dict[str, float] = Field(
        default_factory=dict, description="agent_id -> puntuación de confianza [-1, 1]"
    )
    last_reasoning: str | None = Field(
        default=None,
        description="Razonamiento interno del último tick, para el Inspector de Conciencia",
    )


class MarketOffer(MoneyModel):
    offer_id: str
    seller_id: str
    asset_type: AssetType
    quantity: int = Field(gt=0)
    unit_price: SimCoin
    created_at_tick: int


class Contract(MoneyModel):
    contract_id: str
    party_a: str
    party_b: str
    terms: str
    amount: SimCoin
    status: ContractStatus = ContractStatus.PENDING
    created_at_tick: int


class Transaction(MoneyModel):
    transaction_id: str
    from_agent: str
    to_agent: str
    amount: SimCoin
    reason: str
    tick: int
    timestamp: datetime


class JudgeRuling(MoneyModel):
    ruling_id: str
    contract_id: str
    at_fault_agent: str
    verdict: str
    penalty: SimCoin
    ruled_at_tick: int


class JudgeVerdict(MoneyModel):
    """Salida cruda del LLM del Agente Juez, antes de convertirse en `JudgeRuling`."""

    at_fault_agent: str
    verdict: str
    penalty: SimCoin


class InboxMessage(BaseModel):
    message_id: str
    from_agent: str
    to_agent: str
    body: str
    tick: int


class PerceivedContext(MoneyModel):
    """Lo que un agente percibe al inicio de su tick (fase Perceive)."""

    self_state: AgentState
    inbox: list[InboxMessage]
    market_offers: list[MarketOffer]
    energy_price: SimCoin
    current_tick: int


class AgentAction(BaseModel):
    """Formato JSON estricto que el LLM debe producir en la fase Act."""

    action_type: ActionType
    reasoning: str = Field(description="Razonamiento interno expuesto al Inspector de Conciencia")
    payload: dict[str, str | int | float] = Field(default_factory=dict)


class EconomicIndicators(BaseModel):
    """Métricas macro agregadas para los paneles de telemetría."""

    gini_index: float = Field(ge=0.0, le=1.0)
    inflation_rate: float
    virtual_gdp: float
    transactions_per_minute: float


class TickEvent(BaseModel):
    """Payload difundido por WebSocket en cada tick al frontend."""

    tick: int
    timestamp: datetime
    agents: list[AgentState]
    indicators: EconomicIndicators
