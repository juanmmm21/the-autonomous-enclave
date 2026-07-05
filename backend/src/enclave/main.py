"""FastAPI app factory: cablea configuración, servicios de dominio y el
TickEngine, y arranca el bucle de ticks en segundo plano durante el lifespan
de la aplicación."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from enclave.api.v1.router import router as v1_router
from enclave.api.v1.websocket import TelemetryHub
from enclave.api.v1.websocket import router as websocket_router
from enclave.config import Settings, get_settings
from enclave.services.agent_runtime import AgentRuntime
from enclave.services.contracts import ContractRegistry
from enclave.services.economy import CentralBank
from enclave.services.judge import JudgeAgent
from enclave.services.llm_client import OllamaJudgeBackend, OllamaLLMBackend
from enclave.services.memory_store import QdrantMemoryStore
from enclave.services.message_broker import RedisMessageBroker
from enclave.services.tick_engine import TickEngine

logger = logging.getLogger("enclave.main")


async def _tick_loop(engine: TickEngine, interval_seconds: float) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        await engine.run_tick()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    llm_backend = OllamaLLMBackend(settings.ollama_url, settings.ollama_model)
    judge_backend = OllamaJudgeBackend(settings.ollama_url, settings.judge_ollama_model)
    broker = RedisMessageBroker(settings.redis_url)
    memory_store = QdrantMemoryStore(settings.qdrant_url, settings.ollama_url)
    bank = CentralBank(Decimal(settings.passive_tick_cost))
    contracts = ContractRegistry()
    runtime = AgentRuntime(llm_backend, broker, bank, contracts)
    telemetry_hub = TelemetryHub()
    tick_engine = TickEngine(
        runtime, bank, energy_price=Decimal("1.0"), on_tick=telemetry_hub.broadcast
    )
    judge = JudgeAgent(judge_backend, contracts, bank)

    app.state.settings = settings
    app.state.tick_engine = tick_engine
    app.state.telemetry_hub = telemetry_hub
    app.state.judge = judge
    app.state.memory_store = memory_store

    tick_task = asyncio.create_task(_tick_loop(tick_engine, settings.tick_interval_seconds))
    logger.info("enclave started: tick interval=%.1fs", settings.tick_interval_seconds)

    try:
        yield
    finally:
        tick_task.cancel()
        await asyncio.gather(tick_task, return_exceptions=True)
        await llm_backend.aclose()
        await judge_backend.aclose()
        await broker.aclose()
        await memory_store.aclose()
        logger.info("enclave shut down cleanly")


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="The Autonomous Enclave", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(v1_router, prefix="/api/v1", tags=["enclave"])
    app.include_router(websocket_router, prefix="/api/v1")
    return app


app = create_app()
