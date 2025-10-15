from __future__ import annotations

import abc
from typing import Any, Dict, Optional


class LLMResponse(dict):
    """Typed mapping returned by providers."""

    text: str  # type: ignore[assignment]
    usage: Dict[str, Any]  # type: ignore[assignment]


class BaseLLMProvider(abc.ABC):
    """Abstract interface for narration providers."""

    def __init__(self, create_params: Dict[str, Any]) -> None:
        self.create_params = create_params

    @abc.abstractmethod
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        context: Optional[str] = None,
    ) -> LLMResponse:
        """Generate a narration block."""


PROVIDER_REGISTRY: Dict[str, type[BaseLLMProvider]] = {}


def register_provider(name: str):
    """Decorator used by provider implementations to self-register."""

    def decorator(cls: type[BaseLLMProvider]) -> type[BaseLLMProvider]:
        PROVIDER_REGISTRY[name] = cls
        return cls

    return decorator


def get_provider(name: str) -> type[BaseLLMProvider]:
    if name not in PROVIDER_REGISTRY:
        raise KeyError(f"Unknown provider '{name}'. Registered: {list(PROVIDER_REGISTRY)}")
    return PROVIDER_REGISTRY[name]
