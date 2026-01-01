"""Dynamic scoring logic for model selection."""
from typing import List, Tuple, Optional, Dict
from app.services.dynamic_router.models import ModelConfig
from app.services.dynamic_router.intent import RouterIntent, TaskType


def capability_score(model: ModelConfig, intent: RouterIntent) -> float:
    """
    Score how well a model matches the task type based on its strengths.

    Returns a score from 0-1.
    """
    # Map task types to required capability tags
    task_to_capabilities: Dict[TaskType, List[str]] = {
        "generic_chat": ["chat", "creative_writing", "reasoning"],
        "web_research": ["web_search", "multi_doc_rag"],
        "deep_reasoning": ["reasoning"],
        "coding": ["coding"],
        "math": ["math", "reasoning"],
        "summarization": ["summarization"],
        "document_analysis": ["summarization", "multi_doc_rag"],
        "creative_writing": ["creative_writing"],
    }

    needed = task_to_capabilities.get(intent.task_type, [])
    if not needed:
        return 0.3  # Neutral score for unknown task types

    # Count how many required capabilities the model has
    overlap = sum(1 for tag in needed if tag in model.strengths)
    return overlap / len(needed) if needed else 0.3


def latency_score(model: ModelConfig) -> float:
    """
    Score based on latency (lower is better).

    Normalizes 500ms-4000ms into 1-0.
    """
    min_latency = 500
    max_latency = 4000
    clamped = max(min_latency, min(model.avg_latency_ms, max_latency))
    return 1.0 - (clamped - min_latency) / (max_latency - min_latency)


def cost_score(model: ModelConfig) -> float:
    """
    Score based on cost (cheaper is better).

    Normalizes $0.0005-$0.005 per 1k tokens into 1-0.
    """
    min_cost = 0.0005
    max_cost = 0.005
    clamped = max(min_cost, min(model.cost_per_1k_tokens, max_cost))
    return 1.0 - (clamped - min_cost) / (max_cost - min_cost)


def historical_reward(
    model: ModelConfig, intent: RouterIntent, db_reward: Optional[float] = None
) -> float:
    """
    Score based on historical performance.

    Args:
        model: Model config
        intent: Router intent
        db_reward: Optional reward from database (0-1), None if no data

    Returns:
        Reward score (0-1), defaults to 0.5 if no data
    """
    if db_reward is not None:
        return db_reward
    return 0.5  # Neutral until we have feedback data


def score_model(
    model: ModelConfig, intent: RouterIntent, historical_reward_value: Optional[float] = None
) -> float:
    """
    Compute overall score for a model given an intent.

    Args:
        model: Model configuration
        intent: Router intent
        historical_reward_value: Optional historical reward from DB

    Returns:
        Overall score (0-1), higher is better
    """
    cap = capability_score(model, intent)
    lat = latency_score(model)
    cost = cost_score(model)
    hist = historical_reward(model, intent, historical_reward_value)

    # Weight components based on priority
    if intent.priority == "quality":
        w_quality = 0.6
        w_speed = 0.2
        w_cost = 0.2
    elif intent.priority == "speed":
        w_quality = 0.3
        w_speed = 0.5
        w_cost = 0.2
    elif intent.priority == "cost":
        w_quality = 0.3
        w_speed = 0.2
        w_cost = 0.5
    else:
        # Balanced default
        w_quality = 0.4
        w_speed = 0.3
        w_cost = 0.3

    # Quality component combines capability and historical performance
    quality_component = 0.7 * cap + 0.3 * hist

    # Final weighted score
    return w_quality * quality_component + w_speed * lat + w_cost * cost


def sort_models_by_score(
    models: List[ModelConfig], intent: RouterIntent, historical_rewards: Optional[Dict[str, float]] = None
) -> List[Tuple[ModelConfig, float]]:
    """
    Score and sort models by their suitability for the intent.

    Args:
        models: List of model configs to score
        intent: Router intent
        historical_rewards: Optional dict mapping model.id -> reward (0-1)

    Returns:
        List of (model, score) tuples, sorted by score descending
    """
    if historical_rewards is None:
        historical_rewards = {}

    scored = []
    for model in models:
        # Check context window constraint
        if model.max_context < intent.estimated_input_tokens:
            continue  # Skip models that can't handle the context

        hist_reward = historical_rewards.get(model.id)
        score = score_model(model, intent, hist_reward)
        scored.append((model, score))

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored











