"""Integration helpers for dynamic router."""
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.provider_key import ProviderKey, ProviderType
from app.services.dynamic_router.route_query import route_query, RouteDecision
from app.services.dynamic_router.models import get_model_by_id
from app.services.provider_keys import get_api_key_for_org


async def get_available_providers(
    db: AsyncSession, org_id: str
) -> List[ProviderType]:
    """Get list of providers available for an org."""
    stmt = select(ProviderKey).where(
        ProviderKey.org_id == org_id,
        ProviderKey.is_active == "true",
    )
    result = await db.execute(stmt)
    keys = result.scalars().all()
    return [key.provider for key in keys]


async def get_historical_rewards(
    db: AsyncSession, org_id: Optional[str] = None
) -> Dict[str, float]:
    """
    Get historical reward scores for models.

    Returns dict mapping model.id -> average reward (0-1).
    For now, returns empty dict (neutral) until we have feedback data.
    """
    # TODO: Implement actual query when we have feedback data
    # For now, return empty dict (will use neutral 0.5 in scoring)
    return {}


async def route_with_dynamic_router(
    user_message: str,
    context_summary: str,
    db: AsyncSession,
    org_id: str,
    router_api_key: Optional[str] = None,
) -> RouteDecision:
    """
    Route a query using the dynamic router.

    Args:
        user_message: User's message
        context_summary: Optional context summary
        db: Database session
        org_id: Organization ID
        router_api_key: Optional OpenAI API key for router LLM

    Returns:
        RouteDecision with chosen model and intent
    """
    # Get available providers for this org
    available_providers = await get_available_providers(db, org_id)

    # Get historical rewards (empty for now)
    historical_rewards = await get_historical_rewards(db, org_id)

    # Route the query
    decision = await route_query(
        user_message=user_message,
        context_summary=context_summary,
        router_api_key=router_api_key,
        available_providers=available_providers,
        historical_rewards=historical_rewards,
    )

    return decision





