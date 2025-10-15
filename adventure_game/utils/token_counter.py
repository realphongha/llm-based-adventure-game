from __future__ import annotations

from typing import Iterable


try:  # pragma: no cover - optional dependency
    import tiktoken
except ImportError:  # pragma: no cover - fallback approximation
    tiktoken = None  # type: ignore[assignment]


def count_tokens(chunks: Iterable[str], *, model: str = "gpt-4o-mini") -> int:
    text = "".join(chunks)
    if tiktoken is None:
        return max(1, len(text) // 4)
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))
