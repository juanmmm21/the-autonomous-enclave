"""Telemetría en tiempo real: cada `TickEvent` emitido por el `TickEngine` se
difunde a todos los clientes WebSocket conectados (el mapa Phaser y los
paneles de datos del frontend)."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from enclave.models import TickEvent

logger = logging.getLogger("enclave.telemetry")

router = APIRouter()


class TelemetryHub:
    """Registro de conexiones WebSocket activas. Se usa como callback `on_tick`
    del `TickEngine` para difundir cada tick a todos los clientes suscritos."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[TickEvent]] = set()

    def subscribe(self) -> asyncio.Queue[TickEvent]:
        queue: asyncio.Queue[TickEvent] = asyncio.Queue(maxsize=32)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[TickEvent]) -> None:
        self._subscribers.discard(queue)

    async def broadcast(self, event: TickEvent) -> None:
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("telemetry subscriber queue full, dropping tick %d", event.tick)


@router.websocket("/ws/telemetry")
async def telemetry_stream(websocket: WebSocket) -> None:
    hub: TelemetryHub = websocket.app.state.telemetry_hub
    await websocket.accept()
    queue = hub.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_text(event.model_dump_json())
    except WebSocketDisconnect:
        logger.info("telemetry client disconnected")
    finally:
        hub.unsubscribe(queue)
