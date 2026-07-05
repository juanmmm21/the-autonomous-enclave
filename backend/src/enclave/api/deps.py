"""Dependencias FastAPI: acceden al estado compartido de la aplicación
(`app.state`), poblado una única vez en el lifespan de `main.py`."""

from __future__ import annotations

from fastapi import Request

from enclave.services.tick_engine import TickEngine


def get_tick_engine(request: Request) -> TickEngine:
    return request.app.state.tick_engine  # type: ignore[no-any-return]
