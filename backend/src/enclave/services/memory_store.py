"""Base vectorial persistente para el ciclo de sueño: cada resumen diario se
embebe (vía el endpoint de embeddings de Ollama) y se guarda en Qdrant para
recuperación semántica en jornadas futuras, evitando el desbordamiento de la
ventana de contexto del LLM."""

from __future__ import annotations

import uuid

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from enclave.exceptions import EnclaveError

_COLLECTION_NAME = "enclave_memories"


class MemoryEmbeddingError(EnclaveError):
    """El servicio de embeddings local falló al vectorizar un texto."""


class QdrantMemoryStore:
    """Implementación de `MemoryStore` contra Qdrant, con embeddings de Ollama."""

    def __init__(
        self,
        qdrant_url: str,
        ollama_url: str,
        embedding_model: str = "nomic-embed-text",
        vector_size: int = 768,
    ) -> None:
        self._qdrant = AsyncQdrantClient(url=qdrant_url)
        self._embedding_client = httpx.AsyncClient(base_url=ollama_url.rstrip("/"), timeout=30.0)
        self._embedding_model = embedding_model
        self._vector_size = vector_size
        self._collection_ready = False

    async def _ensure_collection(self) -> None:
        if self._collection_ready:
            return
        existing = await self._qdrant.collection_exists(_COLLECTION_NAME)
        if not existing:
            await self._qdrant.create_collection(
                collection_name=_COLLECTION_NAME,
                vectors_config=VectorParams(size=self._vector_size, distance=Distance.COSINE),
            )
        self._collection_ready = True

    async def _embed(self, text: str) -> list[float]:
        try:
            response = await self._embedding_client.post(
                "/api/embeddings", json={"model": self._embedding_model, "prompt": text}
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MemoryEmbeddingError(f"embedding request failed: {exc}") from exc
        embedding: list[float] = response.json()["embedding"]
        return embedding

    async def store_daily_summary(self, agent_id: str, day: int, summary: str) -> str:
        await self._ensure_collection()
        vector = await self._embed(summary)
        point_id = str(uuid.uuid4())
        await self._qdrant.upsert(
            collection_name=_COLLECTION_NAME,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"agent_id": agent_id, "day": day, "summary": summary},
                )
            ],
        )
        return point_id

    async def retrieve_relevant_memories(
        self, agent_id: str, query: str, top_k: int = 5
    ) -> list[str]:
        await self._ensure_collection()
        vector = await self._embed(query)
        results = await self._qdrant.query_points(
            collection_name=_COLLECTION_NAME,
            query=vector,
            query_filter=Filter(
                must=[FieldCondition(key="agent_id", match=MatchValue(value=agent_id))]
            ),
            limit=top_k,
        )
        return [point.payload["summary"] for point in results.points if point.payload]

    async def aclose(self) -> None:
        await self._embedding_client.aclose()
        await self._qdrant.close()
