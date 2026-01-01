"""Main routing function that combines intent classification and model scoring."""
from typing import Optional, List, Dict, Union
from dataclasses import dataclass
import random

from app.services.dynamic_router.models import ModelConfig, MODELS, get_models_by_provider
from app.services.dynamic_router.intent import RouterIntent, get_router_intent
from app.services.dynamic_router.score import sort_models_by_score
from app.models.provider_key import ProviderType


@dataclass
class RouteDecision:
    """Result of routing decision."""

    chosen_model: ModelConfig
    intent: RouterIntent
    scores: List[Dict[str, Union[float, str]]]  # List of {modelId, score} dicts
    reason: str


async def route_query(
    user_message: str,
    context_summary: str = "",
    router_api_key: Optional[str] = None,
    available_providers: Optional[List[ProviderType]] = None,
    historical_rewards: Optional[Dict[str, float]] = None,
    epsilon: float = 0.1,
) -> RouteDecision:
    """
    Route a query to the best model using dynamic scoring.

    Args:
        user_message: User's message
        context_summary: Optional summary of conversation context
        router_api_key: OpenAI API key for router LLM (if None, uses env var)
        available_providers: Optional list of available providers (if None, uses all)
        historical_rewards: Optional dict mapping model.id -> reward (0-1)
        epsilon: Exploration rate (0-1), probability of choosing second-best for learning

    Returns:
        RouteDecision with chosen model, intent, and scores
    """
    # Step 1: Get router intent
    intent = await get_router_intent(user_message, context_summary, router_api_key)

    # Step 2: Filter models by available providers
    candidate_models = MODELS
    if available_providers:
        candidate_models = [
            m for m in MODELS if m.provider in available_providers
        ]

    # Step 3: Hard override for web search
    if intent.requires_web:
        web_candidates = [
            m for m in candidate_models if "web_search" in m.strengths
        ]
        if web_candidates:
            # Score web-capable models
            scored = sort_models_by_score(web_candidates, intent, historical_rewards)
            if scored:
                chosen = scored[0][0]
                return RouteDecision(
                    chosen_model=chosen,
                    intent=intent,
                    scores=[
                        {"modelId": m.id, "score": s} for m, s in scored[:5]
                    ],
                    reason=f"Web search required - {chosen.display_name}",
                )

    # Step 4: Score all candidate models
    scored = sort_models_by_score(candidate_models, intent, historical_rewards)

    if not scored:
        # Fallback: use first available model
        fallback = candidate_models[0] if candidate_models else MODELS[0]
        return RouteDecision(
            chosen_model=fallback,
            intent=intent,
            scores=[{"modelId": fallback.id, "score": 0.5}],
            reason=f"Fallback - no suitable models found",
        )

    # Step 5: Epsilon-greedy exploration (optional)
    chosen_model = scored[0][0]
    if random.random() < epsilon and len(scored) > 1:
        # 10% of the time, explore second-best for learning
        chosen_model = scored[1][0]

    return RouteDecision(
        chosen_model=chosen_model,
        intent=intent,
        scores=[{"modelId": m.id, "score": float(s)} for m, s in scored[:5]],
        reason=f"Dynamic routing - {chosen_model.display_name} (task: {intent.task_type}, priority: {intent.priority})",
    )











