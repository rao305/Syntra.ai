"""API endpoints for managing user-provided API keys."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, Field
import logging

from app.database import get_db
from app.api.deps import get_current_user_optional, CurrentUser
from app.services.api_key_service import APIKeyService
from app.core.exceptions import ValidationError, NotFoundError
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def require_auth(user: CurrentUser) -> CurrentUser:
    """Require authentication for API key operations."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user


# =============================================================================
# SCHEMAS
# =============================================================================

class APIKeyCreate(BaseModel):
    """Request to add a new API key."""
    provider: str = Field(..., description="Provider name (openai, gemini, etc.)")
    api_key: str = Field(..., min_length=10, description="The API key from the provider")
    key_name: Optional[str] = Field(None, description="User-friendly name for this key")
    validate: bool = Field(True, description="Whether to validate the key")


class APIKeyUpdate(BaseModel):
    """Request to update an API key."""
    api_key: Optional[str] = Field(None, min_length=10)
    key_name: Optional[str] = None
    is_active: Optional[bool] = None


class APIKeyResponse(BaseModel):
    """API key response (never includes actual key)."""
    id: str
    provider: str
    key_name: Optional[str]
    is_active: bool
    validation_status: str
    last_validated_at: Optional[str]
    total_requests: int
    total_tokens_used: int
    last_used_at: Optional[str]
    created_at: str


class ProvidersResponse(BaseModel):
    """Available providers."""
    providers: List[dict]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/providers", response_model=ProvidersResponse)
async def get_providers():
    """Get list of supported providers."""
    providers = [
        {
            'id': 'openai',
            'name': 'OpenAI',
            'description': 'GPT-4, GPT-4o, GPT-4o-mini',
            'signup_url': 'https://platform.openai.com/api-keys',
            'docs_url': 'https://platform.openai.com/docs',
        },
        {
            'id': 'gemini',
            'name': 'Google Gemini',
            'description': 'Gemini Pro, Gemini Flash',
            'signup_url': 'https://makersuite.google.com/app/apikey',
            'docs_url': 'https://ai.google.dev/docs',
        },
        {
            'id': 'anthropic',
            'name': 'Anthropic Claude',
            'description': 'Claude 3 Opus, Sonnet, Haiku',
            'signup_url': 'https://console.anthropic.com/account/keys',
            'docs_url': 'https://docs.anthropic.com/',
        },
        {
            'id': 'perplexity',
            'name': 'Perplexity',
            'description': 'Sonar models with web search',
            'signup_url': 'https://www.perplexity.ai/settings/api',
            'docs_url': 'https://docs.perplexity.ai/',
        },
        {
            'id': 'kimi',
            'name': 'Kimi (Moonshot)',
            'description': 'Moonshot AI models',
            'signup_url': 'https://platform.moonshot.cn/console/api-keys',
            'docs_url': 'https://platform.moonshot.cn/docs',
        },
    ]

    return {"providers": providers}


@router.post("/", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def add_api_key(
    data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_optional)
):
    """
    Add a new API key for a provider.
    The key will be encrypted before storage.
    """
    current_user = require_auth(current_user)

    try:
        service = APIKeyService(db, current_user.id)
        key = await service.add_api_key(
            provider=data.provider,
            api_key=data.api_key,
            key_name=data.key_name,
            validate=data.validate
        )

        return APIKeyResponse(**key.to_dict())

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    provider: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_optional)
):
    """List all API keys for the current user."""
    current_user = require_auth(current_user)

    service = APIKeyService(db, current_user.id)
    keys = await service.get_api_keys(provider=provider, active_only=active_only)

    return [APIKeyResponse(**key.to_dict()) for key in keys]


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_optional)
):
    """Get a specific API key."""
    current_user = require_auth(current_user)

    try:
        service = APIKeyService(db, current_user.id)
        key = await service.get_api_key(key_id)

        return APIKeyResponse(**key.to_dict())

    except NotFoundError:
        raise HTTPException(status_code=404, detail="API key not found")


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    data: APIKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_optional)
):
    """Update an API key."""
    current_user = require_auth(current_user)

    try:
        service = APIKeyService(db, current_user.id)
        key = await service.update_api_key(
            key_id=key_id,
            api_key=data.api_key,
            key_name=data.key_name,
            is_active=data.is_active
        )

        return APIKeyResponse(**key.to_dict())

    except NotFoundError:
        raise HTTPException(status_code=404, detail="API key not found")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{key_id}/validate")
async def validate_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_optional)
):
    """Validate an API key by making a test call."""
    current_user = require_auth(current_user)

    try:
        service = APIKeyService(db, current_user.id)
        is_valid = await service.validate_api_key(key_id)

        return {
            "is_valid": is_valid,
            "message": "API key is valid" if is_valid else "API key is invalid"
        }

    except NotFoundError:
        raise HTTPException(status_code=404, detail="API key not found")


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_optional)
):
    """Delete an API key."""
    current_user = require_auth(current_user)

    try:
        service = APIKeyService(db, current_user.id)
        await service.delete_api_key(key_id)

    except NotFoundError:
        raise HTTPException(status_code=404, detail="API key not found")
