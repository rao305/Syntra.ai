"""Authentication endpoints for Firebase-backed sign-in."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.org import Org
from app.models.user import User, UserRole
# from app.services.firebase_admin_client import verify_firebase_token
from app.services.token_service import create_access_token
from config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


class FirebaseAuthRequest(BaseModel):
    """Payload from the client containing the Firebase ID token."""

    id_token: str = Field(..., min_length=10)


class AuthenticatedUser(BaseModel):
    """Serialized user payload returned to the client."""

    id: str
    email: str
    name: Optional[str] = None


class FirebaseAuthResponse(BaseModel):
    """Response envelope including the app-specific session token."""

    access_token: str
    token_type: str = "bearer"
    org_id: str
    user: AuthenticatedUser


async def _get_default_org(db: AsyncSession) -> Org:
    """Resolve the default org used for Firebase sign-ins."""
    if not settings.default_org_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DEFAULT_ORG_ID is not configured",
        )

    stmt = select(Org).where(Org.id == settings.default_org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if org:
        return org

    # Fallback to slug lookup (handy if env stores slug instead of id)
    stmt = select(Org).where(Org.slug == settings.default_org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if org:
        return org

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Default org not found. Seed the database or update DEFAULT_ORG_ID.",
    )


class ClerkAuthRequest(BaseModel):
    """Payload from the client containing the Clerk token."""

    clerk_token: str = Field(..., min_length=10)
    email: Optional[str] = None


@router.post("/clerk", response_model=FirebaseAuthResponse)
async def exchange_clerk_token(
    payload: ClerkAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify a Clerk token and mint a Syntra session token.

    This endpoint:
    1. Verifies the Clerk token validity
    2. Gets user info from Clerk
    3. Creates or updates the user in the database
    4. Assigns the user to the default org
    5. Returns a JWT access token for API calls
    """
    from app.services.clerk_client import verify_clerk_token

    try:
        # Verify Clerk token and get user info
        clerk_user = await verify_clerk_token(payload.clerk_token)

        if not clerk_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Clerk token",
            )

        # Get or create the default org
        default_org = await _get_default_org(db)

        # Extract user email
        user_email = payload.email or clerk_user.get("email")
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided or found in Clerk token",
            )

        # Get or create user in database
        stmt = select(User).where(
            User.email == user_email,
            User.org_id == default_org.id,
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Create new user
            user = User(
                email=user_email,
                org_id=default_org.id,
                name=clerk_user.get("name") or clerk_user.get("given_name", ""),
                email_verified=datetime.utcnow() if clerk_user.get("email_verified") else None,
                role=UserRole.MEMBER,
            )
            db.add(user)
            await db.flush()
        else:
            # Update last login and email verified status
            user.last_login = datetime.utcnow()
            if clerk_user.get("email_verified") and not user.email_verified:
                user.email_verified = datetime.utcnow()

        await db.commit()

        # Create JWT token for API calls
        access_token = create_access_token(
            subject=user.id,
            org_id=default_org.id,
            email=user.email,
        )

        return FirebaseAuthResponse(
            access_token=access_token,
            org_id=default_org.id,
            user=AuthenticatedUser(
                id=user.id,
                email=user.email,
                name=user.name or None,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error exchanging Clerk token: {e}")
        # Return more detailed error for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to authenticate with Clerk: {str(e)}",
        )


# Firebase endpoint disabled - migrated to Clerk
# @router.post("/firebase", response_model=FirebaseAuthResponse)
# async def exchange_firebase_token(
#     payload: FirebaseAuthRequest,
#     db: AsyncSession = Depends(get_db),
# ):
#     """Verify a Firebase ID token and mint a DAC session token."""
#     # Disabled - migrated to Clerk authentication
#     pass
