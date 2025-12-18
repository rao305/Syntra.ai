"""Provider API endpoints."""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field
import httpx
from datetime import datetime

from app.database import get_db
from app.models.provider_key import ProviderKey, ProviderType
from app.models.org import Org
from app.security import encryption_service, set_rls_context
from app.api.deps import require_org_id
from app.services.ratelimit import get_usage
from app.services.memory_guard import memory_guard
from config import get_settings

settings = get_settings()

router = APIRouter()


class SaveProviderKeyRequest(BaseModel):
    """Request to save a provider API key."""
    provider: ProviderType
    api_key: str = Field(..., min_length=1)
    key_name: Optional[str] = None


class ProviderStatus(BaseModel):
    """Provider configuration status."""
    provider: str
    configured: bool
    key_name: Optional[str] = None
    last_used: Optional[datetime] = None
    masked_key: Optional[str] = None
    usage: Optional["ProviderUsage"] = None  # type: ignore[name-defined]


class ProviderUsage(BaseModel):
    """Per-provider usage snapshot."""

    requests_today: int
    tokens_today: int
    request_limit: int
    token_limit: int


class MemoryStatusResponse(BaseModel):
    """Memory subsystem status."""

    enabled: bool
    message: str
    last_checked: Optional[datetime] = None


class ProviderStatusResponse(BaseModel):
    """Envelope around provider statuses."""

    providers: list[ProviderStatus]
    memory_status: MemoryStatusResponse


ProviderStatus.model_rebuild()


class TestConnectionRequest(BaseModel):
    """Request to test provider connection."""
    provider: ProviderType
    api_key: Optional[str] = None  # Optional: test with provided key or use stored key


class TestConnectionResponse(BaseModel):
    """Response from testing provider connection."""
    provider: str
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


@router.post("/{org_id}/providers")
async def save_provider_key(
    org_id: str,
    request: SaveProviderKeyRequest,
    header_org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Save/update encrypted provider API key.

    This endpoint implements the BYOK (Bring Your Own Key) vault with server-side encryption.
    """
    if header_org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="x-org-id header mismatch"
        )

    # Set RLS context
    await set_rls_context(db, org_id)

    # Encrypt the API key
    encrypted_key = encryption_service.encrypt(request.api_key)

    # Check if key already exists for this org+provider
    stmt = select(ProviderKey).where(
        ProviderKey.org_id == org_id,
        ProviderKey.provider == request.provider
    )
    result = await db.execute(stmt)
    existing_key = result.scalar_one_or_none()

    if existing_key:
        # Update existing key
        stmt = update(ProviderKey).where(
            ProviderKey.id == existing_key.id
        ).values(
            encrypted_key=encrypted_key,
            key_name=request.key_name,
            updated_at=datetime.utcnow()
        )
        await db.execute(stmt)
    else:
        # Create new key
        new_key = ProviderKey(
            org_id=org_id,
            provider=request.provider,
            encrypted_key=encrypted_key,
            key_name=request.key_name
        )
        db.add(new_key)

    await db.commit()

    return {
        "message": "Provider key saved successfully",
        "provider": request.provider.value,
        "masked_key": f"{request.api_key[:8]}...{request.api_key[-4:]}"
    }


@router.get("/{org_id}/providers/status", response_model=ProviderStatusResponse)
async def get_provider_status(
    org_id: str,
    header_org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get masked provider configuration status.

    Returns list of all providers with their configuration status.
    Does not return actual keys, only masked versions for display.
    """
    if header_org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="x-org-id header mismatch"
        )

    # Set RLS context
    await set_rls_context(db, org_id)

    # Get all configured providers for this org
    stmt = select(ProviderKey).where(
        ProviderKey.org_id == org_id,
        ProviderKey.is_active == "true"
    )
    result = await db.execute(stmt)
    configured_keys = result.scalars().all()

    org_stmt = select(Org).where(Org.id == org_id)
    org_result = await db.execute(org_stmt)
    org = org_result.scalar_one_or_none()
    request_limit = (org.requests_per_day if org else None) or settings.default_requests_per_day
    token_limit = (org.tokens_per_day if org else None) or settings.default_tokens_per_day

    # Build status for all providers
    statuses = []
    configured_providers = {key.provider for key in configured_keys}

    for provider_type in ProviderType:
        if provider_type in configured_providers:
            key = next(k for k in configured_keys if k.provider == provider_type)
            # Decrypt only to show masked version
            decrypted = encryption_service.decrypt(key.encrypted_key)
            masked = f"{decrypted[:8]}...{decrypted[-4:]}" if len(decrypted) > 12 else "***"

            usage_snapshot = await get_usage(org_id, provider_type, request_limit, token_limit)

            statuses.append(ProviderStatus(
                provider=provider_type.value,
                configured=True,
                key_name=key.key_name,
                last_used=key.last_used,
                masked_key=masked,
                usage=ProviderUsage(
                    requests_today=usage_snapshot.requests,
                    tokens_today=usage_snapshot.tokens,
                    request_limit=usage_snapshot.request_limit,
                    token_limit=usage_snapshot.token_limit,
                )
            ))
        else:
            usage_snapshot = await get_usage(org_id, provider_type, request_limit, token_limit)
            statuses.append(ProviderStatus(
                provider=provider_type.value,
                configured=False,
                key_name=None,
                last_used=None,
                masked_key=None,
                usage=ProviderUsage(
                    requests_today=usage_snapshot.requests,
                    tokens_today=usage_snapshot.tokens,
                    request_limit=usage_snapshot.request_limit,
                    token_limit=usage_snapshot.token_limit,
                )
            ))

    memory_status = memory_guard.status()

    return ProviderStatusResponse(
        providers=statuses,
        memory_status=MemoryStatusResponse(
            enabled=memory_status.enabled,
            message=memory_status.message,
            last_checked=memory_status.last_checked,
        )
    )


@router.post("/{org_id}/providers/test", response_model=TestConnectionResponse)
async def test_provider_connection(
    org_id: str,
    request: TestConnectionRequest,
    header_org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
    response: Any = None  # Will be injected by FastAPI
):
    """
    Test connection to a provider with provided or stored API key.

    This is the health check endpoint for Phase 1 exit criteria.
    Makes a simple API call to verify the key works.
    """
    if header_org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="x-org-id header mismatch"
        )

    # Set RLS context
    await set_rls_context(db, org_id)

    # Get API key (from request or database)
    api_key = request.api_key

    if not api_key:
        # Fetch from database
        stmt = select(ProviderKey).where(
            ProviderKey.org_id == org_id,
            ProviderKey.provider == request.provider,
            ProviderKey.is_active == "true"
        )
        result = await db.execute(stmt)
        stored_key = result.scalar_one_or_none()

        if not stored_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No API key configured for {request.provider.value}"
            )

        api_key = encryption_service.decrypt(stored_key.encrypted_key)

    # Test the connection based on provider
    try:
        if request.provider == ProviderType.PERPLEXITY:
            success, message, details = await _test_perplexity(api_key)
        elif request.provider == ProviderType.OPENAI:
            success, message, details = await _test_openai(api_key)
        elif request.provider == ProviderType.GEMINI:
            success, message, details = await _test_gemini(api_key)
        elif request.provider == ProviderType.OPENROUTER:
            success, message, details = await _test_openrouter(api_key)
        elif request.provider == ProviderType.KIMI:
            success, message, details = await _test_kimi(api_key)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown provider: {request.provider}"
            )

        # Update last_used timestamp if using stored key
        if not request.api_key:
            stmt = update(ProviderKey).where(
                ProviderKey.org_id == org_id,
                ProviderKey.provider == request.provider
            ).values(last_used=datetime.utcnow())
            await db.execute(stmt)
            await db.commit()

        result = TestConnectionResponse(
            provider=request.provider.value,
            success=success,
            message=message,
            details=details
        )

        # Set provider header for observability tracking
        if response:
            response.headers["X-Provider"] = request.provider.value

        return result

    except Exception as e:
        result = TestConnectionResponse(
            provider=request.provider.value,
            success=False,
            message=f"Connection test failed: {str(e)}",
            details=None
        )

        if response:
            response.headers["X-Provider"] = request.provider.value

        return result


async def _test_perplexity(api_key: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
    """Test Perplexity API connection."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 10
                },
                timeout=10.0
            )

            if response.status_code == 200:
                return True, "Connection successful", {"status_code": 200}
            elif response.status_code == 401:
                return False, "Invalid API key", {"status_code": 401}
            else:
                return False, f"Unexpected response: {response.status_code}", {"status_code": response.status_code}

        except httpx.TimeoutException:
            return False, "Request timeout", None
        except Exception as e:
            return False, f"Error: {str(e)}", None


async def _test_openai(api_key: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
    """Test OpenAI API connection."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={
                    "Authorization": f"Bearer {api_key}"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                models = response.json()
                return True, "Connection successful", {"model_count": len(models.get("data", []))}
            elif response.status_code == 401:
                # Try to get more detailed error from response
                try:
                    error_detail = response.json()
                    error_msg = error_detail.get("error", {}).get("message", "Invalid API key")
                    return False, f"Invalid API key: {error_msg}", {"status_code": 401, "detail": error_detail}
                except ValueError as json_error:
                    logger.warning(f"Failed to parse 401 error response as JSON: {json_error}")
                    return False, "Invalid API key (401 Unauthorized)", {"status_code": 401}
                except Exception as e:
                    logger.exception(f"Unexpected error parsing 401 response: {e}")
                    return False, "Invalid API key (401 Unauthorized)", {"status_code": 401}
            else:
                try:
                    error_data = response.json()
                    return False, f"Error {response.status_code}: {error_data}", {"status_code": response.status_code, "response": error_data}
                except ValueError as json_error:
                    logger.warning(f"Failed to parse error response as JSON: {json_error}")
                    return False, f"Unexpected response: {response.status_code}", {"status_code": response.status_code}
                except Exception as e:
                    logger.exception(f"Unexpected error parsing response: {e}")
                    return False, f"Unexpected response: {response.status_code}", {"status_code": response.status_code}

        except httpx.TimeoutException:
            return False, "Request timeout", None
        except Exception as e:
            return False, f"Error: {str(e)}", None


async def _test_gemini(api_key: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
    """Test Gemini API connection."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
                timeout=10.0
            )

            if response.status_code == 200:
                models = response.json()
                return True, "Connection successful", {"model_count": len(models.get("models", []))}
            elif response.status_code == 400:
                error_data = response.json()
                if "API_KEY_INVALID" in str(error_data):
                    return False, "Invalid API key", {"status_code": 400}
                return False, f"Bad request: {error_data}", {"status_code": 400}
            else:
                return False, f"Unexpected response: {response.status_code}", {"status_code": response.status_code}

        except httpx.TimeoutException:
            return False, "Request timeout", None
        except Exception as e:
            return False, f"Error: {str(e)}", None


async def _test_openrouter(api_key: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
    """Test OpenRouter API connection."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={
                    "Authorization": f"Bearer {api_key}"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                models = response.json()
                return True, "Connection successful", {"model_count": len(models.get("data", []))}
            elif response.status_code == 401:
                return False, "Invalid API key", {"status_code": 401}
            else:
                return False, f"Unexpected response: {response.status_code}", {"status_code": response.status_code}

        except httpx.TimeoutException:
            return False, "Request timeout", None
        except Exception as e:
            return False, f"Error: {str(e)}", None


async def _test_kimi(api_key: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
    """Test Kimi (Moonshot AI) API connection."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.moonshot.ai/v1/models",
                headers={
                    "Authorization": f"Bearer {api_key}"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                models = response.json()
                return True, "Connection successful", {"model_count": len(models.get("data", []))}
            elif response.status_code == 401:
                try:
                    error_detail = response.json()
                    error_msg = error_detail.get("error", {}).get("message", "Invalid API key")
                    return False, f"Invalid API key: {error_msg}", {"status_code": 401, "detail": error_detail}
                except ValueError as json_error:
                    logger.warning(f"Failed to parse 401 error response as JSON: {json_error}")
                    return False, "Invalid API key (401 Unauthorized)", {"status_code": 401}
                except Exception as e:
                    logger.exception(f"Unexpected error parsing 401 response: {e}")
                    return False, "Invalid API key (401 Unauthorized)", {"status_code": 401}
            else:
                try:
                    error_data = response.json()
                    return False, f"Error {response.status_code}: {error_data}", {"status_code": response.status_code, "response": error_data}
                except ValueError as json_error:
                    logger.warning(f"Failed to parse error response as JSON: {json_error}")
                    return False, f"Unexpected response: {response.status_code}", {"status_code": response.status_code}
                except Exception as e:
                    logger.exception(f"Unexpected error parsing response: {e}")
                    return False, f"Unexpected response: {response.status_code}", {"status_code": response.status_code}

        except httpx.TimeoutException:
            return False, "Request timeout", None
        except Exception as e:
            return False, f"Error: {str(e)}", None
