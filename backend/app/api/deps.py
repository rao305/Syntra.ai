"""Shared API dependencies."""
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from app.services.token_service import TokenVerificationError, verify_access_token

import logging
logger = logging.getLogger(__name__)


@dataclass
class CurrentUser:
    """Authenticated user context."""

    id: str
    org_id: str
    email: Optional[str] = None


async def get_current_user_optional(
    authorization: Optional[str] = Header(default=None),
) -> Optional[CurrentUser]:
    """Attempt to resolve the authenticated user from a Bearer token.

    Returns None for invalid/expired tokens since this is optional authentication.
    Only raises exceptions for malformed headers (not missing/invalid tokens).
    """
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        # Return None instead of raising - malformed auth is treated as no auth
        return None

    try:
        payload = verify_access_token(token)
        return CurrentUser(id=payload["sub"], org_id=payload["org_id"], email=payload.get("email"))
    except TokenVerificationError as exc:
        # Invalid/expired token - return None instead of raising
        # This allows requests with x-org-id header to proceed
        logger.warning("⚠️  Token verification failed (treating as unauthenticated): {exc}")
        return None


async def require_org_id(
    x_org_id: Optional[str] = Header(default=None),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
) -> str:
    """
    Ensure requests include the tenant identifier.

    Prefers the explicit `x-org-id` header but falls back to the authenticated user.
    """
    if x_org_id:
        return x_org_id

    if current_user:
        return current_user.org_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing x-org-id header",
    )


def validate_user_access(
    current_user: Optional[CurrentUser],
    requested_user_id: Optional[str] = None
) -> None:
    """
    SECURITY: Validate that user can only access/modify their own data.

    Prevents user impersonation by ensuring:
    1. User is authenticated
    2. User can only modify their own user_id
    3. User cannot spoof other users in the organization

    Args:
        current_user: Authenticated user from token
        requested_user_id: User ID being operated on (from request)

    Raises:
        HTTPException: 403 Forbidden if user lacks permission
    """
    # If no user_id is being requested, no validation needed
    if not requested_user_id:
        return

    # User must be authenticated to perform operations
    if not current_user:
        logger.warning(
            f"Unauthenticated request attempted to access user data: {requested_user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for user operations"
        )

    # User can only modify their own data
    if current_user.id != requested_user_id:
        logger.warning(
            f"User {current_user.id} attempted to access data for user {requested_user_id}",
            extra={
                "authenticated_user": current_user.id,
                "requested_user": requested_user_id,
                "org_id": current_user.org_id,
            }
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot access other users' data"
        )
