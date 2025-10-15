from __future__ import annotations

from typing import Any, Dict, List, Optional

from .llm_provider.base import BaseLLMProvider


class LogSummarizer:
    """Summarize adventure logs to keep context tight."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        *,
        threshold_tokens: int = 1500,
        min_turns: int = 5,
    ) -> None:
        self.provider = provider
        self.threshold_tokens = threshold_tokens
        self.min_turns = min_turns

    def should_summarize(self, *, total_tokens: int, turn_count: int) -> bool:
        return total_tokens >= self.threshold_tokens and turn_count >= self.min_turns

    def summarize(self, log: List[Dict[str, Any]]) -> str:
        transcript = "\n".join(
            f"Turn {entry['turn']} - Player: {entry['player']} | Narrator: {entry['narrator']}"
            for entry in log
        )
        try:
            response = self.provider.generate(
                system_prompt=(
                    "Summarize the session so far into a concise yet vivid recap. "
                    "Keep it under 120 words and preserve mysteries."
                ),
                user_prompt=transcript,
                context=None,
            )
            return response["text"].strip()
        except Exception:
            return transcript[-300:]
