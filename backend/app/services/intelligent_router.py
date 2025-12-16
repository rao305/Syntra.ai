"""Intelligent router for LLM selection.

This service makes smart routing decisions based on:
1. Query classification (type, complexity)
2. Available providers for the org
3. Recent performance metrics
4. Cost considerations (PRIORITIZED)
5. Provider-specific capabilities

Inspired by the Collaborative Memory paper's coordinator concept.

Cost optimization: Always choose the cheapest model that can handle the query well.
"""
from __future__ import annotations

from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.provider_key import ProviderType, ProviderKey
from app.services.query_classifier import query_classifier, QueryClassification
from app.services.model_registry import get_valid_models, is_valid_model


# Cost per 1M tokens (input/output average) - Updated pricing as of 2024
MODEL_COSTS = {
    # OpenAI
    (ProviderType.OPENAI, "gpt-4o"): 2.50,  # $2.50 per 1M tokens (avg)
    (ProviderType.OPENAI, "gpt-4o-mini"): 0.15,  # $0.15 per 1M tokens (avg) - VERY CHEAP
    (ProviderType.OPENAI, "o1"): 15.00,  # $15 per 1M tokens - expensive reasoning
    (ProviderType.OPENAI, "o1-mini"): 3.00,  # $3 per 1M tokens

    # Gemini
    (ProviderType.GEMINI, "gemini-2.5-pro"): 1.25,  # $1.25 per 1M tokens
    (ProviderType.GEMINI, "gemini-2.5-flash"): 0.075,  # $0.075 per 1M tokens - CHEAPEST
    (ProviderType.GEMINI, "gemini-2.5-pro"): 1.25,
    (ProviderType.GEMINI, "gemini-2.5-flash"): 0.075,

    # Perplexity
    (ProviderType.PERPLEXITY, "sonar-pro"): 3.00,  # $3 per 1M tokens (with search)
    (ProviderType.PERPLEXITY, "sonar"): 1.00,  # $1 per 1M tokens
    (ProviderType.PERPLEXITY, "sonar-reasoning-pro"): 5.00,  # $5 per 1M tokens
    (ProviderType.PERPLEXITY, "sonar-reasoning"): 1.00,

    # Kimi (Moonshot AI)
    (ProviderType.KIMI, "moonshot-v1-8k"): 0.12,  # ~$0.12 per 1M tokens
    (ProviderType.KIMI, "moonshot-v1-32k"): 0.24,
    (ProviderType.KIMI, "moonshot-v1-128k"): 0.60,
    (ProviderType.KIMI, "kimi-k2-turbo-preview"): 0.30,
}


@dataclass
class RoutingDecision:
    """Result of intelligent routing."""

    provider: ProviderType
    model: str
    reason: str
    classification: QueryClassification
    fallback_options: List[Tuple[ProviderType, str]]


class IntelligentRouter:
    """Makes intelligent routing decisions for LLM selection."""

    def __init__(self):
        self._performance_cache = {}  # Could be enhanced with Redis later

    async def route(
        self,
        db: AsyncSession,
        org_id: str,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        preferred_provider: Optional[ProviderType] = None,
        preferred_model: Optional[str] = None
    ) -> RoutingDecision:
        """
        Make an intelligent routing decision.

        Args:
            db: Database session
            org_id: Organization ID
            query: User's query
            conversation_history: Previous messages
            preferred_provider: Optional provider preference
            preferred_model: Optional model preference

        Returns:
            RoutingDecision with provider, model, and reason
        """
        # Step 1: Classify the query
        classification = query_classifier.classify(query, conversation_history)

        # Step 2: Get available providers for this org
        available_providers = await self._get_available_providers(db, org_id)

        # Step 3: If user specified preferences, validate and use them
        if preferred_provider and preferred_model:
            if preferred_provider in available_providers:
                if is_valid_model(preferred_provider, preferred_model):
                    fallbacks = self._get_fallback_options(
                        classification,
                        available_providers,
                        exclude_provider=preferred_provider
                    )
                    return RoutingDecision(
                        provider=preferred_provider,
                        model=preferred_model,
                        reason=f"User-specified {preferred_provider.value} with {preferred_model}",
                        classification=classification,
                        fallback_options=fallbacks
                    )

        # Step 4: Check if recommended provider is available
        if classification.recommended_provider in available_providers:
            provider = classification.recommended_provider
            model = classification.recommended_model

            # Validate model is still supported
            if is_valid_model(provider, model):
                fallbacks = self._get_fallback_options(
                    classification,
                    available_providers,
                    exclude_provider=provider
                )
                return RoutingDecision(
                    provider=provider,
                    model=model,
                    reason=classification.reason,
                    classification=classification,
                    fallback_options=fallbacks
                )

        # Step 5: Recommended provider not available, find best alternative
        alternative = self._find_best_alternative(
            classification,
            available_providers
        )

        if alternative:
            provider, model, reason = alternative
            fallbacks = self._get_fallback_options(
                classification,
                available_providers,
                exclude_provider=provider
            )
            return RoutingDecision(
                provider=provider,
                model=model,
                reason=f"{reason} (recommended {classification.recommended_provider.value} not available)",
                classification=classification,
                fallback_options=fallbacks
            )

        # Step 6: Fallback to any available provider
        return self._fallback_to_any_available(
            available_providers,
            classification
        )

    async def _get_available_providers(
        self,
        db: AsyncSession,
        org_id: str
    ) -> Set[ProviderType]:
        """Get providers that are configured for this org."""
        stmt = select(ProviderKey).where(
            ProviderKey.org_id == org_id,
            ProviderKey.is_active == "true"
        )
        result = await db.execute(stmt)
        keys = result.scalars().all()

        # TEMPORARY: Exclude Perplexity during QA test (API key invalid)
        providers = {key.provider for key in keys}
        providers.discard(ProviderType.PERPLEXITY)
        return providers

    def _get_model_cost(self, provider: ProviderType, model: str) -> float:
        """Get cost per 1M tokens for a model. Returns high value if unknown."""
        return MODEL_COSTS.get((provider, model), 100.0)  # Unknown models = expensive

    def _find_best_alternative(
        self,
        classification: QueryClassification,
        available_providers: Set[ProviderType]
    ) -> Optional[Tuple[ProviderType, str, str]]:
        """
        Find the best alternative provider when recommended one is unavailable.

        STRATEGY: Route based on what each model does BEST
        - OpenAI: Best at code, reasoning, creative writing
        - Perplexity: Best at factual queries (web search)
        - Gemini: Best at simple queries, speed
        - Kimi: Best at multilingual

        Within each tier, prefer lower cost when quality is similar.
        """
        from app.services.query_classifier import QueryType

        # Define capability tiers (ordered by what's BEST for each task)
        priority_map = {
            QueryType.FACTUAL: [
                # Tier 1: Web search - Perplexity is BEST
                [(ProviderType.PERPLEXITY, "sonar"), (ProviderType.PERPLEXITY, "sonar-pro")],
                # Tier 2: Fallback - no web search
                [(ProviderType.OPENAI, "gpt-4o-mini"), (ProviderType.GEMINI, "gemini-2.5-flash")],
            ],
            QueryType.CODE: [
                # Tier 1: OpenAI is BEST at code
                [(ProviderType.OPENAI, "gpt-4o-mini")],
                # Tier 2: Gemini as fallback
                [(ProviderType.GEMINI, "gemini-2.5-flash")],
            ],
            QueryType.CREATIVE: [
                # Tier 1: OpenAI is BEST at creative writing
                [(ProviderType.OPENAI, "gpt-4o-mini")],
                # Tier 2: Gemini as fallback
                [(ProviderType.GEMINI, "gemini-2.5-pro")],
            ],
            QueryType.REASONING: [
                # Tier 1: OpenAI is BEST at reasoning
                [(ProviderType.OPENAI, "gpt-4o-mini")],
                # Tier 2: Gemini as fallback
                [(ProviderType.GEMINI, "gemini-2.5-flash")],
            ],
            QueryType.ANALYSIS: [
                # Tier 1: OpenAI is BEST at analysis
                [(ProviderType.OPENAI, "gpt-4o-mini")],
                # Tier 2: Gemini as fallback
                [(ProviderType.GEMINI, "gemini-2.5-flash")],
            ],
            QueryType.MULTILINGUAL: [
                # Tier 1: Kimi is BEST at multilingual
                [(ProviderType.KIMI, "moonshot-v1-32k")],
                # Tier 2: Gemini as fallback
                [(ProviderType.GEMINI, "gemini-2.5-pro")],
            ],
            QueryType.SIMPLE: [
                # Tier 1: Gemini is good for simple queries (fast & cheap)
                [(ProviderType.GEMINI, "gemini-2.5-flash")],
                # Tier 2: OpenAI as fallback
                [(ProviderType.OPENAI, "gpt-4o-mini")],
            ],
            QueryType.CONVERSATION: [
                # Tier 1: Gemini for quick conversation
                [(ProviderType.GEMINI, "gemini-2.5-flash")],
                # Tier 2: OpenAI as fallback
                [(ProviderType.OPENAI, "gpt-4o-mini")],
            ],
        }

        tiers = priority_map.get(classification.query_type, [])

        # Try each tier in order
        for tier in tiers:
            # Try each model in the tier
            for provider, model in tier:
                if provider in available_providers and is_valid_model(provider, model):
                    return (
                        provider,
                        model,
                        f"Best for {classification.query_type.value} - {provider.value}'s strength"
                    )

        return None

    def _get_fallback_options(
        self,
        classification: QueryClassification,
        available_providers: Set[ProviderType],
        exclude_provider: Optional[ProviderType] = None
    ) -> List[Tuple[ProviderType, str]]:
        """Get fallback options in priority order."""
        fallbacks = []

        # Get alternative provider
        alt = self._find_best_alternative(classification, available_providers)
        if alt:
            provider, model, _ = alt
            if provider != exclude_provider:
                fallbacks.append((provider, model))

        # Add more general fallbacks
        general_fallbacks = [
            (ProviderType.OPENAI, "gpt-4o-mini"),
            (ProviderType.GEMINI, "gemini-2.5-flash"),
            (ProviderType.PERPLEXITY, "sonar")
        ]

        for provider, model in general_fallbacks:
            if provider in available_providers and provider != exclude_provider:
                if is_valid_model(provider, model):
                    if (provider, model) not in fallbacks:
                        fallbacks.append((provider, model))

        return fallbacks[:3]  # Return top 3 fallbacks

    def _fallback_to_any_available(
        self,
        available_providers: Set[ProviderType],
        classification: QueryClassification
    ) -> RoutingDecision:
        """Fallback when no good options are found."""
        # Try common providers in order
        fallback_order = [
            (ProviderType.OPENAI, "gpt-4o-mini"),
            (ProviderType.GEMINI, "gemini-2.5-flash"),
            (ProviderType.PERPLEXITY, "sonar"),
            (ProviderType.KIMI, "moonshot-v1-8k")
        ]

        for provider, model in fallback_order:
            if provider in available_providers:
                if is_valid_model(provider, model):
                    return RoutingDecision(
                        provider=provider,
                        model=model,
                        reason=f"Fallback to {provider.value} - limited providers available",
                        classification=classification,
                        fallback_options=[]
                    )

        # Last resort - raise error
        raise ValueError(
            f"No suitable providers available for org. "
            f"Available providers: {', '.join(p.value for p in available_providers)}"
        )

    def record_performance(
        self,
        provider: ProviderType,
        model: str,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None
    ):
        """Record performance metrics for future routing decisions."""
        # Simple in-memory cache for now
        # Could be enhanced with Redis or database storage
        key = f"{provider.value}:{model}"

        if key not in self._performance_cache:
            self._performance_cache[key] = {
                "success_count": 0,
                "error_count": 0,
                "total_latency": 0.0,
                "request_count": 0
            }

        stats = self._performance_cache[key]
        stats["request_count"] += 1

        if success:
            stats["success_count"] += 1
            stats["total_latency"] += latency_ms
        else:
            stats["error_count"] += 1

    def get_performance_stats(
        self,
        provider: ProviderType,
        model: str
    ) -> Optional[Dict]:
        """Get performance stats for a provider/model combination."""
        key = f"{provider.value}:{model}"
        stats = self._performance_cache.get(key)

        if not stats or stats["request_count"] == 0:
            return None

        return {
            "provider": provider.value,
            "model": model,
            "success_rate": stats["success_count"] / stats["request_count"],
            "avg_latency_ms": stats["total_latency"] / max(stats["success_count"], 1),
            "error_rate": stats["error_count"] / stats["request_count"],
            "total_requests": stats["request_count"]
        }


# Singleton instance
intelligent_router = IntelligentRouter()
