from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración cargada desde variables de entorno (ver `.env.example`)."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ENCLAVE_")

    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    postgres_dsn: str = "postgresql://enclave:enclave@localhost:5432/enclave"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    judge_ollama_model: str = "phi4"

    tick_interval_seconds: float = 5.0
    passive_tick_cost: str = "1.0"
    """Coste pasivo por tick en SimCoin, como string para preservar precisión Decimal."""

    ticks_per_day: int = 10
    """Cada cuántos ticks se ejecuta el ciclo de sueño (compresión de memoria)."""


def get_settings() -> Settings:
    return Settings()
