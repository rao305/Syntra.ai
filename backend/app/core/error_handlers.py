"""Centralized error handling and exception handlers."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError
import logging
import traceback
from typing import Dict, Any
import json

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "INVALID_REQUEST",
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationAPIError(APIError):
    """Validation error."""

    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationAPIError(APIError):
    """Authentication error."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED"
        )


class AuthorizationAPIError(APIError):
    """Authorization error."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN"
        )


class NotFoundAPIError(APIError):
    """Resource not found error."""

    def __init__(self, resource: str, identifier: str = ""):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"

        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND"
        )


class ConflictAPIError(APIError):
    """Resource conflict error."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT"
        )


class RateLimitAPIError(APIError):
    """Rate limit error."""

    def __init__(self, message: str = "Too many requests", retry_after: int = 60):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMITED",
            details={"retry_after": retry_after}
        )


class InternalServerError(APIError):
    """Internal server error."""

    def __init__(self, message: str = "Internal server error", error_id: str = ""):
        details = {}
        if error_id:
            details["error_id"] = error_id

        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_ERROR",
            details=details
        )


def format_error_response(error: APIError) -> Dict[str, Any]:
    """Format error response in standard format."""
    response = {
        "error": {
            "code": error.error_code,
            "message": error.message
        }
    }

    if error.details:
        response["error"]["details"] = error.details

    return response


def log_error(request: Request, error: Exception, status_code: int) -> None:
    """Log error with context (never expose traceback in response)."""
    # Only include traceback in logs for 5xx errors (server errors)
    extra = {
        "path": request.url.path,
        "method": request.method,
        "error": str(error),
    }

    # SECURITY: Only log traceback for 5xx errors, never for client errors
    if status_code >= 500:
        extra["traceback"] = traceback.format_exc()

    logger.error(
        f"API Error: {status_code}",
        extra=extra
    )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions."""
    log_error(request, exc, exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(exc)
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic ValidationError."""
    error = ValidationAPIError(
        "Request validation failed",
        details={
            "errors": [
                {
                    "field": error["loc"][-1],
                    "message": error["msg"]
                }
                for error in exc.errors()
            ]
        }
    )
    log_error(request, exc, error.status_code)
    return JSONResponse(
        status_code=error.status_code,
        content=format_error_response(error)
    )


async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database errors."""
    logger.error(f"Database error: {str(exc)}", exc_info=True)

    # Handle integrity errors (e.g., unique constraint violations)
    if isinstance(exc, IntegrityError):
        error = ConflictAPIError("Resource already exists or database constraint violation")
    else:
        error = InternalServerError("Database error occurred")

    return JSONResponse(
        status_code=error.status_code,
        content=format_error_response(error)
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions (never expose details to client)."""
    # Log full exception details server-side
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )

    # Return generic error to client (never expose exception details)
    error = InternalServerError("An unexpected error occurred")
    return JSONResponse(
        status_code=error.status_code,
        content=format_error_response(error)
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers with FastAPI app."""
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
