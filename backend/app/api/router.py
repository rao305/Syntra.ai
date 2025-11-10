"""Router API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional
import re

from app.database import get_db

router = APIRouter()


class ChooseProviderRequest(BaseModel):
    """Request to choose a provider."""
    message: str = Field(..., min_length=1)
    context_size: Optional[int] = None  # Number of messages in thread
    thread_id: Optional[str] = None


class ChooseProviderResponse(BaseModel):
    """Response with chosen provider."""
    provider: str
    model: str
    reason: str


def analyze_content(message: str, context_size: int = 0) -> tuple[str, str, str]:
    """
    Rule-based provider selection logic.

    Rules:
    1. Questions with "search", "latest", "recent", "news" -> Perplexity (web-grounded)
    2. Questions needing structured output (JSON, code) -> OpenAI (function calling)
    3. Long documents or large context (>10 messages) -> Gemini (long context)
    4. Default or fallback scenarios -> OpenRouter (auto-routing)
    """
    message_lower = message.lower()

    # Rule 1: Web-grounded queries
    web_keywords = ["search", "latest", "recent", "news", "current", "today", "what is happening", "find"]
    if any(keyword in message_lower for keyword in web_keywords):
        return "perplexity", "llama-3.1-sonar-small-128k-online", "Web-grounded query detected (news/search/latest)"

    # Rule 2: Structured output
    structured_keywords = ["json", "code", "function", "class", "api", "format", "parse", "extract"]
    if any(keyword in message_lower for keyword in structured_keywords):
        return "openai", "gpt-4o-mini", "Structured output required (code/JSON/parsing)"

    # Rule 3: Long context
    if context_size and context_size > 10:
        return "gemini", "gemini-1.5-flash", f"Long conversation ({context_size} messages) requires extended context"

    # Rule 4: Question detection (use Perplexity for factual Q&A)
    question_patterns = [r"\?$", r"^(what|who|where|when|why|how)", r"(tell me|explain|describe)"]
    is_question = any(re.search(pattern, message_lower) for pattern in question_patterns)
    if is_question:
        return "perplexity", "llama-3.1-sonar-small-128k-online", "Factual question detected"

    # Default: OpenRouter for auto-routing
    return "openrouter", "auto", "General query - using auto-router for best selection"


@router.post("/choose", response_model=ChooseProviderResponse)
async def choose_provider(
    request: ChooseProviderRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Choose best provider for a request using rule-based routing.

    This implements Phase 1 routing logic based on content analysis.
    Phase 2 will add cost optimization, latency tracking, and fallback logic.
    """
    provider, model, reason = analyze_content(request.message, request.context_size or 0)

    return ChooseProviderResponse(
        provider=provider,
        model=model,
        reason=reason
    )
