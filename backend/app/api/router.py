"""Router API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional
import re

from app.database import get_db
from app.api.deps import require_org_id
from app.models.provider_key import ProviderType
from app.services.model_registry import validate_and_get_model, get_default_model
from app.services.memory_manager import smooth_intent, update_last_intent

router = APIRouter()


class ChooseProviderRequest(BaseModel):
    """Request to choose a provider."""
    message: str = Field(..., min_length=1)
    context_size: Optional[int] = None  # Number of messages in thread
    thread_id: Optional[str] = None
    has_images: bool = False  # Whether the request contains images


class ChooseProviderResponse(BaseModel):
    """Response with chosen provider."""
    provider: str
    model: str
    reason: str


def analyze_content(message: str, context_size: int = 0, has_images: bool = False) -> tuple[str, str, str]:
    """
    Domain-specialist LLM router - Each provider is an expert agent.
    
    Based on collaborative memory paper's multi-agent framework.
    Each LLM has CLEAR domain specialization and expertise.
    
    ╔══════════════════════════════════════════════════════════════════╗
    ║ AGENT SPECIALIZATIONS (Domain → Expert LLM)                     ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║ 1. GEMINI AGENT                                                  ║
    ║    Domain: Technical Execution & Vision Analysis                 ║
    ║    Best for: Programming, algorithms, image analysis, multimodal ║
    ║    Strength: Fast (TTFT ~300ms), 1M+ token context, vision      ║
    ║                                                                  ║
    ║ 2. OPENAI AGENT                                                  ║
    ║    Domain: Complex Reasoning & Vision Understanding              ║
    ║    Best for: Multi-step logic, analysis, image reasoning, math   ║
    ║    Strength: Superior reasoning, instruction following, vision   ║
    ║                                                                  ║
    ║ 3. KIMI AGENT (Moonshot AI)                                     ║
    ║    Domain: Long-Context Creative Writing (Text Only)             ║
    ║    Best for: Storytelling, articles, essays, long-form content   ║
    ║    Strength: 128k context window, Chinese & English proficiency  ║
    ║                                                                  ║
    ║ 4. PERPLEXITY AGENT                                              ║
    ║    Domain: Real-time Information & Research (Text Only)          ║
    ║    Best for: Current events, news, citations, web-grounded facts║
    ║    Strength: Live web search, always up-to-date, cited sources  ║
    ║                                                                  ║
    ║ 5. FALLBACK AGENT (Perplexity)                                  ║
    ║    Domain: General Conversation & Simple Q&A (Text Only)         ║
    ║    Best for: Casual chat, simple questions, general knowledge    ║
    ╚══════════════════════════════════════════════════════════════════╝
    
    Routing: Query → Domain Detection → Specialist Selection → Response
    """
    
    # ═══════════════════════════════════════════════════════════════════
    # DOMAIN 0: VISION/IMAGE PROCESSING (HIGHEST PRIORITY)
    # ═══════════════════════════════════════════════════════════════════
    if has_images:
        # For images, prefer OpenAI GPT-4o for best vision understanding
        # Fallback to Gemini if OpenAI is not available
        provider = ProviderType.OPENAI
        model = validate_and_get_model(provider, "gpt-4o")
        return provider.value, model, "Vision/image analysis (GPT-4o - superior vision understanding)"
    message_lower = message.lower()
    
    # ═══════════════════════════════════════════════════════════════════
    # DOMAIN 0: SOCIAL GREETINGS (OpenAI Agent) - CHECK FIRST!
    # ═══════════════════════════════════════════════════════════════════
    # Hard override: Greetings → chat model (no web, no citations)
    from app.services.intent_rules import is_social_greeting
    if is_social_greeting(message):
        provider = ProviderType.OPENAI
        model = validate_and_get_model(provider, "gpt-4o-mini")
        return provider.value, model, "Social greeting (OpenAI GPT-4o-mini - conversational, no citations)"

    # ═══════════════════════════════════════════════════════════════════
    # DOMAIN 0: LONG-CONTEXT CREATIVE WRITING (Kimi Agent) - CHECK FIRST!
    # ═══════════════════════════════════════════════════════════════════
    # Specialization: Storytelling, articles, essays, long-form creative content
    # Priority: HIGHEST (check BEFORE code generation to avoid "write a" conflicts)
    creative_writing_keywords = [
        " story", " article", " essay", " blog",  # Note: leading space to avoid "history", "distillery"
        "tell me a story", "create a narrative", "storytelling",
        "long-form", "fiction", "novel", "narrative",
        "chinese", "中文", "translate to chinese", "translate to english",
        "bilingual", "multilingual content"
    ]
    if any(keyword in message_lower for keyword in creative_writing_keywords):
        provider = ProviderType.KIMI
        model = validate_and_get_model(provider, "kimi-k2-turbo-preview")  # 128k context
        return provider.value, model, "Creative writing (Kimi K2 - 128k context, bilingual)"

    # ═══════════════════════════════════════════════════════════════════
    # DOMAIN 1: TECHNICAL EXECUTION (Gemini Agent)
    # ═══════════════════════════════════════════════════════════════════
    # Specialization: Code generation, algorithms, data structures, debugging
    # Priority: HIGH (after creative writing, to avoid conflicts)
    structured_keywords = [
        "json", "code", "function", "class", "api", "tool", "call",
        "format", "parse", "extract", "schema", "structure", "plan",
        "automate", "workflow", "execute", "generate code", "write script",
        "create function", "build api", "implement", "develop",
        # Programming languages
        "python", "javascript", "java", "c++", "rust", "go", "typescript",
        "ruby", "php", "swift", "kotlin", "scala", "html", "css", "sql",
        # Code-related actions
        "algorithm", "program", "script", "write a", "write an", "create a",
        "build a", "make a", "debug", "refactor", "optimize code"
    ]
    if any(keyword in message_lower for keyword in structured_keywords):
        # Code generation: Try OpenAI first (best quality), fallback to Gemini
        provider = ProviderType.OPENAI
        model = validate_and_get_model(provider, "gpt-4o-mini")  # Best at code generation
        return provider.value, model, "Code generation (GPT-4o-mini - superior programming)"

    # ═══════════════════════════════════════════════════════════════════
    # DOMAIN 2: COMPLEX REASONING (OpenAI Agent)
    # ═══════════════════════════════════════════════════════════════════
    # Specialization: Multi-step logic, analysis, creative writing, mathematics
    # Priority: HIGH (after code, before research)
    reasoning_keywords = [
        "analyze", "compare", "contrast", "evaluate", "assess", "critique",
        "explain", "why", "reason", "logic", "think", "solve",
        "calculate", "math", "equation", "proof", "theorem",
        "creative", "write a story", "poem", "essay", "article",
        "brainstorm", "ideate", "design thinking", "strategy",
        "multi-step", "complex", "detailed analysis", "deep dive"
    ]
    if any(keyword in message_lower for keyword in reasoning_keywords):
        provider = ProviderType.OPENAI
        model = validate_and_get_model(provider, "gpt-4o-mini")  # Fast reasoning model
        return provider.value, model, "Complex reasoning (GPT-4o-mini - superior logic)"

    # ═══════════════════════════════════════════════════════════════════
    # DOMAIN 3: REAL-TIME INFORMATION (Perplexity Agent)
    # ═══════════════════════════════════════════════════════════════════
    # Specialization: Current events, news, citations, web-grounded facts
    # Strength: Live web search with sources, always up-to-date
    research_keywords = [
        "latest", "recent", "news", "current", "today", "now",
        "what is happening", "cite", "source", "research",
        "latest news", "breaking", "update", "discover", "investigate",
        "analyze trends", "market research", "competitive analysis",
        "events", "happening", "developments", "situation", "status",
        "web search", "google", "look up"
    ]
    if any(keyword in message_lower for keyword in research_keywords):
        provider = ProviderType.PERPLEXITY
        model = validate_and_get_model(provider, "sonar")  # Fast, real-time web search
        return provider.value, model, "Real-time research (Perplexity Sonar - live web search)"

    # Rule 3: Very long context → Gemini
    # Gemini supports ~1M tokens for large PDFs/codebases (DAC 3.1, 5.3)
    # Context size > 10 messages indicates need for extended context window
    if context_size and context_size > 10:
        provider = ProviderType.GEMINI
        model = validate_and_get_model(provider, "gemini-2.5-pro")  # 2M token context, best for long conversations
        return provider.value, model, f"Long conversation ({context_size} msgs - Gemini 1.5 Pro, 2M tokens)"

    # Also route to Gemini for explicit long-document queries
    # Enhanced detection based on DAC paper's document analysis scenarios
    long_doc_keywords = [
        "pdf", "document", "file", "codebase", "repository",
        "long", "entire", "whole", "full text", "analyze document",
        "summarize", "extract from", "process document", "parse file",
        "codebase analysis", "repository analysis"
    ]
    if any(keyword in message_lower for keyword in long_doc_keywords):
        provider = ProviderType.GEMINI
        model = validate_and_get_model(provider, "gemini-2.5-pro")  # 2M tokens for large documents
        return provider.value, model, "Document analysis (Gemini 1.5 Pro - 2M token context)"

    # Rule 4: Question detection → Perplexity for factual Q&A
    # Perplexity with citations provides verifiable factual answers (DAC 3.2)
    # Enhanced question patterns based on DAC paper's Q&A scenarios
    # BUT: Skip Perplexity for ambiguous/philosophical questions (they often fail)
    ambiguous_keywords = [
        "meaning of life", "universe and everything", "make me a sandwich",
        "philosophical", "existential", "abstract", "remind me"
    ]
    is_ambiguous = any(keyword in message_lower for keyword in ambiguous_keywords)
    
    if is_ambiguous:
        # Route ambiguous queries to Gemini (better at handling vague requests)
        provider = ProviderType.GEMINI
        model = validate_and_get_model(provider, "gemini-2.5-flash")
        return provider.value, model, "Ambiguous query (Gemini 1.5 Flash - handles vague requests)"
    
    question_patterns = [
        r"\?$",  # Ends with question mark
        r"^(what|who|where|when|why|how|which|can|could|should|would)",  # Question words
        r"(tell me|explain|describe|define|compare|contrast|list|identify)",  # Question verbs
        r"(what is|what are|how does|how do|why is|why are)"  # Common question phrases
    ]
    is_question = any(re.search(pattern, message_lower) for pattern in question_patterns)
    if is_question:
        provider = ProviderType.PERPLEXITY
        model = validate_and_get_model(provider, "sonar-pro")  # More precise for factual Q&A
        return provider.value, model, "Factual question (Perplexity Sonar Pro - precise with citations)"

    # ═══════════════════════════════════════════════════════════════════
    # DOMAIN 3: GENERAL KNOWLEDGE (Fallback Agent)
    # ═══════════════════════════════════════════════════════════════════
    # Specialization: Casual chat, simple Q&A, general knowledge
    # Using Perplexity for reliable web-grounded responses
    provider = ProviderType.PERPLEXITY
    model = validate_and_get_model(provider, "sonar")  # Fast, general purpose
    return provider.value, model, "General chat (Perplexity Sonar - web-grounded)"


@router.post("/choose", response_model=ChooseProviderResponse)
async def choose_provider(
    request: ChooseProviderRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Choose best provider for a request using rule-based routing.

    This implements Phase 1 routing logic based on content analysis.
    Phase 2 will add cost optimization, latency tracking, and fallback logic.
    """
    provider_str, model, reason = analyze_content(request.message, request.context_size or 0, request.has_images)
    
    # Extract intent from reason for smoothing
    current_intent = "ambiguous_or_other"  # Default
    intent_keywords = {
        "coding_help": ["code generation", "code", "function", "algorithm"],
        "qa_retrieval": ["explanation", "explain", "what", "how", "why"],
        "editing/writing": ["rewrite", "edit", "writing", "article", "story"],
        "reasoning/math": ["solve", "calculate", "math", "reasoning"],
        "social_chat": ["greeting", "hello", "thanks", "general chat"],
    }
    for intent, keywords in intent_keywords.items():
        if any(kw in reason.lower() for kw in keywords):
            current_intent = intent
            break
    
    # Apply intent smoothing if thread_id is provided
    if request.thread_id:
        smoothed_intent = smooth_intent(current_intent, request.thread_id, request.message)
        # Note: Don't override routing based on intent smoothing - let primary router decide
        # qa_retrieval queries should route through Perplexity (web search) not forced to Gemini

        # Update last intent for next turn
        update_last_intent(request.thread_id, smoothed_intent)
    
    # Ensure we're using a valid ProviderType enum
    try:
        provider = ProviderType(provider_str)
    except ValueError:
        # Fallback to OpenRouter if invalid provider string
        provider = ProviderType.OPENROUTER
        model = validate_and_get_model(provider)
        reason = f"Invalid provider '{provider_str}', using fallback"
    
    # Double-check model is valid for the provider (safety net)
    validated_model = validate_and_get_model(provider, model)
    
    return ChooseProviderResponse(
        provider=provider.value,
        model=validated_model,
        reason=reason
    )
