"""
ai/llm.py
---------
Provider-agnostic LLM interface for the AI analyst layer.

The rest of the codebase talks to `LLMProvider` (an abstract interface) and
never to a vendor SDK directly, so swapping Gemini → Claude later is a one-class
change here, not a rewrite. The active provider is chosen via `LLM_PROVIDER`
(default ``gemini``); see `get_llm`.

Gemini notes (learned by probing the API):
- `gemini-2.5-*` are *thinking* models; with a small `max_output_tokens` the
  thinking budget eats the whole allowance and `response.text` comes back empty.
  We set ``thinking_budget=0`` by default — our tasks (sentiment, briefing) want
  direct output, not chain-of-thought — which makes responses reliable & cheap.
- `gemini-2.0-flash` returned 429 (free-tier quota) and `gemini-2.5-flash`
  intermittently returns 503 (high demand), so the default is the lighter,
  more-available ``gemini-2.5-flash-lite``. Transient 429/503 are retried with
  exponential backoff so a daily pipeline run doesn't fail on a passing spike.
"""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from typing import Any

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")


class LLMProvider(ABC):
    """Minimal text-in/text-out interface every provider must implement."""

    @abstractmethod
    def generate(
        self, prompt: str, *, system: str | None = None,
        temperature: float = 0.4, max_tokens: int = 1024,
    ) -> str:
        """Return the model's text response."""

    @abstractmethod
    def generate_json(
        self, prompt: str, *, system: str | None = None,
        temperature: float = 0.0, max_tokens: int = 2048,
    ) -> Any:
        """Return parsed JSON (the model is asked for application/json)."""


class GeminiProvider(LLMProvider):
    def __init__(
        self, api_key: str | None = None, model: str = DEFAULT_MODEL,
        *, max_retries: int = 4, retry_base_delay: float = 2.0,
    ):
        from google import genai  # imported lazily so importing this module is cheap

        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set — add it to .env")
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    def _config(self, system, temperature, max_tokens, *, json_mode=False):
        from google.genai import types

        kwargs: dict = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            # Disable "thinking": our tasks want direct output, and a small token
            # budget otherwise gets consumed by reasoning, leaving text empty.
            "thinking_config": types.ThinkingConfig(thinking_budget=0),
        }
        if system:
            kwargs["system_instruction"] = system
        if json_mode:
            kwargs["response_mime_type"] = "application/json"
        return types.GenerateContentConfig(**kwargs)

    def _run(self, prompt: str, config) -> str:
        """Call the model, retrying transient 429/503 with exponential backoff."""
        from google.genai import errors as genai_errors

        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                resp = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=config,
                )
                return (resp.text or "").strip()
            except genai_errors.APIError as e:
                transient = isinstance(e, genai_errors.ServerError) or getattr(e, "code", None) == 429
                if not transient or attempt == self.max_retries - 1:
                    raise
                last_exc = e
                time.sleep(self.retry_base_delay * (2 ** attempt))
        raise last_exc  # pragma: no cover — loop always returns or raises above

    def generate(self, prompt, *, system=None, temperature=0.4, max_tokens=1024) -> str:
        return self._run(prompt, self._config(system, temperature, max_tokens))

    def generate_json(self, prompt, *, system=None, temperature=0.0, max_tokens=2048) -> Any:
        text = self._run(prompt, self._config(system, temperature, max_tokens, json_mode=True))
        return json.loads(text or "null")


def get_llm(provider: str | None = None, model: str | None = None) -> LLMProvider:
    """Return the configured LLM provider. Override via `LLM_PROVIDER` / arg."""
    provider = (provider or os.environ.get("LLM_PROVIDER", "gemini")).lower()
    if provider == "gemini":
        return GeminiProvider(model=model or DEFAULT_MODEL)
    raise ValueError(f"Unknown LLM provider: {provider!r}")
