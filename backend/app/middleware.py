"""FastAPI middleware for observability."""
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.observability import metrics_collector, RequestMetrics, classify_error


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request metrics.

    Captures:
    - Request count per path
    - Request latency
    - Error rates and classification
    - Per-org metrics
    - Per-provider metrics
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and track metrics."""
        start_time = time.time()

        # Extract org_id from path if present (e.g., /api/orgs/{org_id}/...)
        org_id = None
        path_parts = request.url.path.split("/")
        if "orgs" in path_parts:
            try:
                org_idx = path_parts.index("orgs")
                if org_idx + 1 < len(path_parts):
                    org_id = path_parts[org_idx + 1]
            except (ValueError, IndexError):
                pass

        # Extract provider from query/body if applicable
        provider = None
        error_class = None
        status_code = 200

        try:
            response: Response = await call_next(request)
            status_code = response.status_code

            # Try to extract provider from response headers (set by provider endpoints)
            provider = response.headers.get("X-Provider")

            return response

        except Exception as e:
            # Classify and record error
            error_class = classify_error(e)
            status_code = 500
            raise

        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Record metrics
            metrics = RequestMetrics(
                path=request.url.path,
                method=request.method,
                status_code=status_code,
                duration_ms=duration_ms,
                org_id=org_id,
                provider=provider,
                error_class=error_class,
            )

            metrics_collector.record_request(metrics)
