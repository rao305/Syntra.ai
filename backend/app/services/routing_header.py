"""
User-visible Transparent Routing Header.

Prepends a small, safe header showing provider/model and repair/fallback status,
without leaking prompts, API keys, or hidden reasoning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Union

from app.models.provider_key import ProviderType


@dataclass(frozen=True)
class RoutingHeaderInfo:
    provider: str
    model: str
    route_reason: str
    context: str  # "full_history" | "context_pack"
    repair_attempts: int  # 0 | 1
    fallback_used: str  # "yes" | "no"


def provider_name(provider: Optional[Union[ProviderType, str]]) -> str:
    """
    Normalize provider name for user-visible output.

    Examples (per spec): openai | google | anthropic | perplexity
    """
    if provider is None:
        return "unknown"
    if isinstance(provider, ProviderType):
        if provider == ProviderType.GEMINI:
            return "google"
        return provider.value
    p = str(provider).strip().lower()
    if not p:
        return "unknown"
    if p in {"gemini", "google"}:
        return "google"
    return p


_SINGLE_LINE_RE = re.compile(r"[\r\n]+")


def _one_line(text: Optional[str]) -> str:
    if not text:
        return "unknown"
    t = _SINGLE_LINE_RE.sub(" ", str(text)).strip()
    t = re.sub(r"\s+", " ", t)
    return t if t else "unknown"


def build_routing_header(info: RoutingHeaderInfo) -> str:
    """
    Render the header in the exact 6-line format required by the spec.
    """
    provider = _one_line(info.provider)
    model = _one_line(info.model)
    reason = _one_line(info.route_reason)
    context = _one_line(info.context)
    repair_attempts = 1 if int(info.repair_attempts) >= 1 else 0
    fallback_used = "yes" if str(info.fallback_used).strip().lower() == "yes" else "no"

    return (
        "ROUTING:\n"
        f"- provider: {provider}\n"
        f"- model: {model}\n"
        f"- route_reason: {reason}\n"
        f"- context: {context}\n"
        f"- repair_attempts: {repair_attempts}\n"
        f"- fallback_used: {fallback_used}\n"
    )


def user_requested_hide_routing(text: Optional[str]) -> bool:
    """
    Detect a user request to hide routing details.

    Per spec, this should disable `transparent_routing` from the next response onward.
    """
    t = (text or "").lower()
    patterns = [
        r"\bhide\b.*\brouting\b",
        r"\bdisable\b.*\brouting\b",
        r"\bturn\s*off\b.*\brouting\b",
        r"\bno\b.*\brouting\b.*\bheader\b",
        r"\bhide\b.*\bprovider\b",
        r"\bhide\b.*\bmodel\b",
        r"\bstop\b.*\bshowing\b.*\brouting\b",
    ]
    return any(re.search(p, t) for p in patterns)

