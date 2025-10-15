from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional

from .base import BaseLLMProvider, LLMResponse, register_provider


try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except ImportError:  # pragma: no cover - fallback when openai not installed
    OpenAI = None  # type: ignore[assignment]


@register_provider("openai")
class OpenAILLM(BaseLLMProvider):
    """GPT powered narrator via OpenAI's API."""

    def __init__(
        self,
        create_params: Dict[str, Any],
    ) -> None:
        super().__init__(create_params)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        if OpenAI is None:
            raise ImportError("openai package is not installed")
        self.client = OpenAI(api_key=api_key)

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        context: Optional[str] = None,
    ) -> LLMResponse:
        messages = [{"role": "system", "content": system_prompt}]
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": user_prompt})

        response = self.client.chat.completions.create(
            **self.create_params,
            messages=messages,
        )

        choice = response.choices[0]
        content = choice.message.content or ""
        usage: Dict[str, Any] = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
        res = LLMResponse(text=content, usage=usage)
        logging.info(res)
        return res
