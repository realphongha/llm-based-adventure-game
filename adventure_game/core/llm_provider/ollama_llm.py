from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import requests

from .base import BaseLLMProvider, LLMResponse, register_provider


@register_provider("ollama")
class OllamaLLM(BaseLLMProvider):
    """Narrator backed by a local Ollama instance."""

    def __init__(
        self,
        *,
        model: str = "llama3",
        host: str = "http://localhost:11434",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.model = model
        self.host = host.rstrip("/")

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        context: Optional[str] = None,
    ) -> LLMResponse:
        body: Dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "options": {"num_predict": self.max_tokens},
            "prompt": _build_prompt(system_prompt, user_prompt, context),
        }

        response = requests.post(f"{self.host}/api/generate", json=body, timeout=60)
        response.raise_for_status()

        text_chunks: list[str] = []
        token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for line in response.iter_lines():
            if not line:
                continue
            payload = json.loads(line)
            if chunk := payload.get("response"):
                text_chunks.append(chunk)
            if "done" in payload and payload["done"] and "total_duration" in payload:
                usage = payload.get("metrics", {})
                token_usage = {
                    "prompt_tokens": usage.get("prompt_eval_count", 0),
                    "completion_tokens": usage.get("eval_count", 0),
                    "total_tokens": usage.get("prompt_eval_count", 0)
                    + usage.get("eval_count", 0),
                }

        return LLMResponse(text="".join(text_chunks).strip(), usage=token_usage)


def _build_prompt(system_prompt: str, user_prompt: str, context: Optional[str]) -> str:
    blocks = [system_prompt]
    if context:
        blocks.append(context)
    blocks.append(user_prompt)
    return "\n\n".join(blocks)
