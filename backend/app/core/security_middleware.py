"""
Security middleware for headers and CORS.
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List
import os


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content Security Policy
        if not request.url.path.startswith("/docs"):  # Allow Swagger UI
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self' https://api.openai.com https://api.anthropic.com "
                "https://generativelanguage.googleapis.com https://openrouter.ai"
            )

        # HSTS (only in production)
        if os.getenv("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


def configure_cors(app: FastAPI) -> None:
    """Configure CORS with secure defaults."""

    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        # Strict CORS in production
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
        allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]

        if not allowed_origins:
            raise ValueError("ALLOWED_ORIGINS must be set in production")

        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            max_age=600,  # Cache preflight for 10 minutes
        )
    else:
        # Permissive CORS in development
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


def configure_security(app: FastAPI) -> None:
    """Configure all security middleware."""
    configure_cors(app)
    app.add_middleware(SecurityHeadersMiddleware)
