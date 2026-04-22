"""OpenRouter LLM client with per-stage routing and fallback."""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel
from openai import AsyncOpenAI
import instructor

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

        # Initialize OpenAI client pointed at OpenRouter
        self._openai_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self._api_key,
        )
        # Wrap with instructor for structured calls
        self._instructor_client = instructor.from_openai(self._openai_client)

    async def call(
        self,
        stage: str,
        messages: list[dict],
        schema: type[BaseModel] | None = None,
        images: list[bytes] | None = None, # Not yet used, but kept for future vision models
        run_id: str | None = None, # For Langfuse, not directly used in LLM call
        **kwargs,
    ) -> Any:
        """Route to correct model based on stage. Handle retries and fallback."""
        stage_config = self._config["stages"].get(stage, self._config["stages"]["extract"])
        primary = stage_config["primary"]
        fallback = stage_config["fallback"]
        retry_config = self._config.get("retry", {})
        # Our decision: try primary once, then fallback once. So 1 attempt per provider.
        attempts = retry_config.get("attempts_per_provider", 1) 
        backoff = retry_config.get("backoff_base_seconds", 2)

        # Build list of models to try (primary, then fallback)
        models_to_try = []
        if primary:
            models_to_try.append(primary)
        if fallback and fallback != primary: # Avoid trying same model twice if fallback is identical
            models_to_try.append(fallback)
        
        if not models_to_try:
            raise LLMError(f"No models configured for stage '{stage}'")

        for model in models_to_try:
            for attempt in range(attempts):
                try:
                    print(f"Calling LLM: model={model}, stage={stage}, attempt={attempt+1}/{attempts}") # Debug print
                    if schema:
                        response = await self._call_with_schema(model, messages, schema, **kwargs)
                    else:
                        response = await self._call_raw(model, messages, **kwargs)
                    return response
                except Exception as e:
                    print(f"LLM call failed for model {model}, attempt {attempt+1}: {e}") # Debug print
                    if attempt < attempts - 1: # If not the last attempt for this model
                        await asyncio.sleep(backoff ** (attempt + 1)) # Exponential backoff
                    else: # Last attempt for this model failed, try next model if available
                        continue # Loop to next model in models_to_try

        raise LLMAllProvidersFailedError(
            f"All configured LLM providers failed for stage '{stage}' after {attempts} attempts each."
        )

    async def _call_raw(self, model: str, messages: list[dict], **kwargs) -> dict:
        """Make a raw OpenRouter API call."""
        completion = await self._openai_client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
        # Extract content from the first choice
        if completion.choices and completion.choices[0].message and completion.choices[0].message.content:
            return {"content": completion.choices[0].message.content}
        return {"content": ""}

    async def _call_with_schema(
        self, model: str, messages: list[dict], schema: type[BaseModel], **kwargs
    ) -> BaseModel:
        """Make an Instructor-backed structured call."""
        structured_response = await self._instructor_client.chat.completions.create(
            model=model,
            messages=messages,
            response_model=schema,
            **kwargs,
        )
        return structured_response
