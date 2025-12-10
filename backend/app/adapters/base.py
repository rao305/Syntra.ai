"""Shared adapter structures."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ProviderResponse:
    """Normalized provider response payload."""

    content: str
    provider_message_id: Optional[str]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    latency_ms: float  # Total response time in milliseconds
    request_id: Optional[str]
    raw: Optional[Dict[str, Any]] = None
    citations: Optional[Any] = None
    ttfs_ms: Optional[float] = None  # Time to first token in milliseconds (for streaming)


class ProviderAdapterError(Exception):
    """Raised when a provider call fails."""

    def __init__(self, provider: str, message: str):
        super().__init__(f"{provider} adapter error: {message}")
        self.provider = provider
        self.message = message
