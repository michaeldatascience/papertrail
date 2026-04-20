"""OpenRouter LLM client with per-stage routing and fallback."""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel

from papertrail.config.loader import get_settings, load_json_config
from papertrail.observability.langfuse_client import get_langfuse


class LLMError(Exception):
    pass


class LLMAllProvidersFailedError(LLMError):
    pass


class LLMClient:
    """LLM client that routes calls through OpenRouter with retry and fallback."""

    def __init__(self):
        settings = get_settings()
        self._config = load_json_config("llm.json")
        self._api_key = settings.openrouter_api_key
        self._langfuse = get_langfuse()

    async def call(
        self,
        stage: str,
        messages: list[dict],
        schema: type[BaseModel] | None = None,
        images: list[bytes] | None = None,
        run_id: str | None = None,
        **kwargs,
    ) -> Any:
        """Route to correct model based on stage. Handle retries and fallback."""
        stage_config = self._config["stages"].get(stage, self._config["stages"]["extract"])
        primary = stage_config["primary"]
        fallback = stage_config["fallback"]
        retry_config = self._config.get("retry", {})
        attempts = retry_config.get("attempts_per_provider", 2)
        backoff = retry_config.get("backoff_base_seconds", 2)

        for model in (primary, fallback):
            for attempt in range(attempts):
                try:
                    if schema:
                        return await self._call_with_schema(model, messages, schema, **kwargs)
                    else:
                        return await self._call_raw(model, messages, **kwargs)
                except Exception:
                    await asyncio.sleep(backoff ** attempt)
                    continue

        raise LLMAllProvidersFailedError(
            f"All providers failed for stage '{stage}'"
        )

    async def _call_raw(self, model: str, messages: list[dict], **kwargs) -> dict:
        """Make a raw OpenRouter API call."""
        # TODO: Implement with openai client pointed at OpenRouter
        raise NotImplementedError("Raw LLM call not yet implemented")

    async def _call_with_schema(
        self, model: str, messages: list[dict], schema: type[BaseModel], **kwargs
    ) -> BaseModel:
        """Make an Instructor-backed structured call."""
        # TODO: Implement with instructor.from_openai
        raise NotImplementedError("Structured LLM call not yet implemented")
