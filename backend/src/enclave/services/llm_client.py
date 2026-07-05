"""Cliente de inferencia contra Ollama. Implementa `LLMBackend` inyectando la
personalidad y el contexto percibido del agente, y forzando salida JSON
estructurada que se valida contra `AgentAction` antes de devolverla."""

from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

from enclave.exceptions import LLMGenerationError
from enclave.models import AgentAction, Contract, JudgeVerdict, PerceivedContext

_ACTION_JSON_SCHEMA_HINT = (
    "Responde EXCLUSIVAMENTE con un objeto JSON con las claves "
    '"action_type" (uno de: move, send_message, post_offer, accept_offer, '
    "sign_contract, file_dispute, transfer, sleep, idle), "
    '"reasoning" (string con tu razonamiento interno) y '
    '"payload" (objeto con los parámetros de la acción). '
    "No incluyas texto fuera del JSON."
)


class OllamaLLMBackend:
    """Implementación de `LLMBackend` contra la API HTTP local de Ollama."""

    def __init__(self, base_url: str, model: str, timeout_seconds: float = 60.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=timeout_seconds)

    async def generate_action(self, system_prompt: str, context: PerceivedContext) -> AgentAction:
        prompt = (
            f"{system_prompt}\n\n"
            f"Contexto percibido este tick:\n{context.model_dump_json()}\n\n"
            f"{_ACTION_JSON_SCHEMA_HINT}"
        )
        try:
            response = await self._client.post(
                "/api/generate",
                json={"model": self._model, "prompt": prompt, "format": "json", "stream": False},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMGenerationError(
                f"ollama request failed for agent {context.self_state.agent_id}: {exc}"
            ) from exc

        raw_output = response.json().get("response", "")
        try:
            action_payload = json.loads(raw_output)
            return AgentAction.model_validate(action_payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMGenerationError(
                f"agent {context.self_state.agent_id} produced a malformed action: {raw_output!r}"
            ) from exc

    async def aclose(self) -> None:
        await self._client.aclose()


_JUDGE_JSON_SCHEMA_HINT = (
    "Responde EXCLUSIVAMENTE con un objeto JSON con las claves "
    '"at_fault_agent" (id del agente responsable del incumplimiento), '
    '"verdict" (string explicando tu razonamiento) y '
    '"penalty" (número, la multa en SimCoin). No incluyas texto fuera del JSON.'
)


class OllamaJudgeBackend:
    """Implementación de `JudgeBackend`: usa un modelo de mayor capacidad de
    razonamiento (ver `Settings.judge_ollama_model`) para resolver disputas."""

    def __init__(self, base_url: str, model: str, timeout_seconds: float = 120.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=timeout_seconds)

    async def adjudicate(
        self, system_prompt: str, contract: Contract, dispute_context: str
    ) -> JudgeVerdict:
        prompt = (
            f"{system_prompt}\n\n"
            f"Contrato en disputa:\n{contract.model_dump_json()}\n\n"
            f"Contexto de la denuncia:\n{dispute_context}\n\n"
            f"{_JUDGE_JSON_SCHEMA_HINT}"
        )
        try:
            response = await self._client.post(
                "/api/generate",
                json={"model": self._model, "prompt": prompt, "format": "json", "stream": False},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMGenerationError(
                f"judge ollama request failed for contract {contract.contract_id}: {exc}"
            ) from exc

        raw_output = response.json().get("response", "")
        try:
            verdict_payload = json.loads(raw_output)
            return JudgeVerdict.model_validate(verdict_payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMGenerationError(
                f"judge produced a malformed verdict for contract "
                f"{contract.contract_id}: {raw_output!r}"
            ) from exc

    async def aclose(self) -> None:
        await self._client.aclose()
