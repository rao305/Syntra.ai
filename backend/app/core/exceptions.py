"""
Custom exceptions and error handling utilities for Syntra.
"""

import logging
import traceback
from typing import Any, Dict, Optional, Type, Callable
from functools import wraps
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class SyntraError(Exception):
    """Base exception for all Syntra errors."""

    def __init__(
        self,
        message: str,
        code: str = "SYNTRA_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(SyntraError):
    """Input validation errors."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field} if field else {}
        )


class AuthenticationError(SyntraError):
    """Authentication failures."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message=message, code="AUTH_ERROR")


class AuthorizationError(SyntraError):
    """Authorization/permission failures."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message=message, code="FORBIDDEN")


class NotFoundError(SyntraError):
    """Resource not found errors."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier}
        )


class ProviderError(SyntraError):
    """AI provider errors (OpenAI, Gemini, etc.)."""

    def __init__(
        self,
        provider: str,
        message: str,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=f"{provider} error: {message}",
            code="PROVIDER_ERROR",
            details={
                "provider": provider,
                "original_error": str(original_error) if original_error else None
            }
        )
        self.provider = provider
        self.original_error = original_error


class RateLimitError(SyntraError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: Optional[int] = None):
        super().__init__(
            message="Rate limit exceeded",
            code="RATE_LIMIT",
            details={"retry_after": retry_after}
        )
        self.retry_after = retry_after


class UsageLimitError(SyntraError):
    """Usage limit exceeded (subscription limits)."""

    def __init__(self, limit_type: str, current: int, max_allowed: int):
        super().__init__(
            message=f"{limit_type} limit exceeded: {current}/{max_allowed}",
            code="USAGE_LIMIT",
            details={"limit_type": limit_type, "current": current, "max": max_allowed}
        )


class DatabaseError(SyntraError):
    """Database operation errors."""

    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details={"operation": operation}
        )


# =============================================================================
# ERROR HANDLING DECORATORS
# =============================================================================

def handle_exceptions(
    reraise_http: bool = True,
    log_level: str = "error",
    default_status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
):
    """
    Decorator to handle exceptions consistently.

    Args:
        reraise_http: If True, HTTPExceptions pass through unchanged
        log_level: Logging level for caught exceptions
        default_status_code: HTTP status code for unhandled exceptions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                if reraise_http:
                    raise
                else:
                    logger.warning(f"HTTPException in {func.__name__}")
                    raise
            except SyntraError as e:
                log_func = getattr(logger, log_level)
                log_func(
                    f"SyntraError in {func.__name__}: {e.message}",
                    extra={"code": e.code, "details": e.details}
                )
                raise HTTPException(
                    status_code=_get_status_code(e),
                    detail={"error": e.code, "message": e.message, "details": e.details}
                )
            except Exception as e:
                logger.exception(f"Unhandled exception in {func.__name__}: {str(e)}")
                raise HTTPException(
                    status_code=default_status_code,
                    detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
                )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HTTPException:
                if reraise_http:
                    raise
                else:
                    logger.warning(f"HTTPException in {func.__name__}")
                    raise
            except SyntraError as e:
                log_func = getattr(logger, log_level)
                log_func(f"SyntraError in {func.__name__}: {e.message}")
                raise HTTPException(
                    status_code=_get_status_code(e),
                    detail={"error": e.code, "message": e.message}
                )
            except Exception as e:
                logger.exception(f"Unhandled exception in {func.__name__}")
                raise HTTPException(
                    status_code=default_status_code,
                    detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
                )

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _get_status_code(error: SyntraError) -> int:
    """Map SyntraError types to HTTP status codes."""
    mapping = {
        ValidationError: status.HTTP_400_BAD_REQUEST,
        AuthenticationError: status.HTTP_401_UNAUTHORIZED,
        AuthorizationError: status.HTTP_403_FORBIDDEN,
        NotFoundError: status.HTTP_404_NOT_FOUND,
        RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
        UsageLimitError: status.HTTP_402_PAYMENT_REQUIRED,
        ProviderError: status.HTTP_502_BAD_GATEWAY,
        DatabaseError: status.HTTP_503_SERVICE_UNAVAILABLE,
    }

    for error_type, code in mapping.items():
        if isinstance(error, error_type):
            return code

    return status.HTTP_500_INTERNAL_SERVER_ERROR


# =============================================================================
# PROVIDER ERROR HANDLING
# =============================================================================

async def handle_provider_call(
    provider: str,
    operation: Callable,
    *args,
    **kwargs
) -> Any:
    """
    Wrapper for AI provider API calls with proper error handling.

    Usage:
        result = await handle_provider_call(
            "openai",
            client.chat.completions.create,
            model="gpt-4o",
            messages=[...]
        )
    """
    import openai
    import httpx

    try:
        return await operation(*args, **kwargs)

    # OpenAI specific errors
    except openai.RateLimitError as e:
        logger.warning(f"{provider} rate limit hit", extra={"error": str(e)})
        raise RateLimitError(retry_after=60)

    except openai.AuthenticationError as e:
        logger.error(f"{provider} authentication failed", extra={"error": str(e)})
        raise ProviderError(provider, "Invalid API key", e)

    except openai.BadRequestError as e:
        logger.warning(f"{provider} bad request", extra={"error": str(e)})
        raise ProviderError(provider, str(e), e)

    except openai.APIConnectionError as e:
        logger.error(f"{provider} connection failed", extra={"error": str(e)})
        raise ProviderError(provider, "Connection failed", e)

    # HTTP errors
    except httpx.TimeoutException as e:
        logger.error(f"{provider} request timeout", extra={"error": str(e)})
        raise ProviderError(provider, "Request timeout", e)

    except httpx.HTTPStatusError as e:
        logger.error(f"{provider} HTTP error", extra={"status": e.response.status_code})
        raise ProviderError(provider, f"HTTP {e.response.status_code}", e)

    # Generic errors
    except Exception as e:
        logger.exception(f"{provider} unexpected error")
        raise ProviderError(provider, f"Unexpected error: {type(e).__name__}", e)

