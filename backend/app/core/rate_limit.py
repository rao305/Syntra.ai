"""Rate limiting middleware for API endpoints."""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
from collections import defaultdict
import asyncio
import logging

logger = logging.getLogger(__name__)


class SimpleRateLimiter:
    """Simple in-memory rate limiter based on client IP."""

    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Number of allowed requests per minute per IP.
        """
        self.requests_per_minute = requests_per_minute
        self.requests: dict = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> bool:
        """
        Check if a request is allowed for the given key.

        Args:
            key: Client identifier (e.g., IP address)

        Returns:
            True if request is allowed, False if rate limit exceeded.
        """
        async with self._lock:
            now = time.time()
            minute_ago = now - 60

            # Clean old requests outside the time window
            self.requests[key] = [t for t in self.requests[key] if t > minute_ago]

            # Check if limit exceeded
            if len(self.requests[key]) >= self.requests_per_minute:
                return False

            # Record this request
            self.requests[key].append(now)
            return True


# Global rate limiter instance (1000 requests/minute per IP for development)
rate_limiter = SimpleRateLimiter(requests_per_minute=1000)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting per client IP."""

    async def dispatch(self, request: Request, call_next):
        """
        Check rate limit and either allow or reject the request.

        Args:
            request: The incoming request.
            call_next: Function to call the next middleware/route handler.

        Returns:
            Response from the next handler, or 429 if rate limit exceeded.
        """
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)

        # Get client IP (handle X-Forwarded-For for reverse proxies)
        client_ip = request.headers.get(
            "X-Forwarded-For", request.client.host if request.client else "unknown"
        )

        # Extract the first IP if X-Forwarded-For contains multiple IPs
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()

        # Check rate limit
        if not await rate_limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please slow down.",
            )

        return await call_next(request)
