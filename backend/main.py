"""FastAPI application entry point."""

# Load environment variables FIRST, before any other imports
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from current directory
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

# Initialize logging after environment is loaded
from app.core.logging_config import setup_logging

setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    json_logs=os.getenv("ENVIRONMENT", "development") == "production",
    log_file=os.getenv("LOG_FILE")
)

import logging
logger = logging.getLogger(__name__)

logger.info("Starting Syntra API...")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import get_settings
from app.database import init_db, close_db
from app.api import router, providers, billing, audit, metrics, query_rewriter, entities, auth, collaboration, dynamic_collaborate, council, eval, quality_analytics
from app.api.api_keys import router as api_keys_router
from app.api.threads import router as threads_router
from app.core.security_middleware import configure_security
from app.core.error_handlers import register_error_handlers
from app.core.rate_limit import RateLimitMiddleware

# Import intelligent router endpoints (Phase 1)
try:
    from api.router_endpoints import router as intelligent_router
    INTELLIGENT_ROUTER_AVAILABLE = True
except ImportError:
    intelligent_router = None
    INTELLIGENT_ROUTER_AVAILABLE = False
from app.middleware import ObservabilityMiddleware
from app.adapters._client import get_client

# OpenTelemetry instrumentation (Phase 4)
try:
    from app.services.otel_instrumentation import instrument_fastapi_app
    OTEL_ENABLED = True
except ImportError:
    OTEL_ENABLED = False
    print("Warning: OpenTelemetry not available (install opentelemetry packages)")

settings = get_settings()


async def warm_provider_connections():
    """Warm HTTP/2 connections to provider APIs on startup."""
    client = await get_client()
    
    # Warm connections to major providers (harmless health checks or no-ops)
    warm_urls = [
        "https://api.perplexity.ai",
        "https://api.openai.com",
        "https://generativelanguage.googleapis.com",
        "https://openrouter.ai",
    ]
    
    for url in warm_urls:
        try:
            # Quick HEAD request to establish connection
            await client.head(url, timeout=5.0)
        except Exception:
            # Ignore errors - this is just warming
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()  # Initialize database connection
    
    # Warm provider connections (HTTP/2 + TLS handshake)
    await warm_provider_connections()
    
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="Cross-LLM Thread Hub",
    description="Multi-tenant B2B SaaS for cross-provider LLM threading",
    version="0.1.0",
    lifespan=lifespan
)

# Security middleware (CORS, headers, etc.)
configure_security(app)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Error handlers
register_error_handlers(app)

# Observability middleware (Phase 1.5)
app.add_middleware(ObservabilityMiddleware)

# OpenTelemetry instrumentation (Phase 4)
if OTEL_ENABLED:
    app = instrument_fastapi_app(app)

# Include routers
app.include_router(threads_router, prefix="/api", tags=["threads"])
app.include_router(router.router, prefix="/api/router", tags=["router"])

# Include intelligent router endpoints (Phase 1)
if INTELLIGENT_ROUTER_AVAILABLE:
    app.include_router(intelligent_router, prefix="/api/router", tags=["intelligent-router"])
app.include_router(providers.router, prefix="/api/orgs", tags=["providers"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])
app.include_router(query_rewriter.router, tags=["query-rewriter"])
app.include_router(entities.router, prefix="/api", tags=["entities"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(api_keys_router, prefix="/api", tags=["api-keys"])
app.include_router(collaboration.router, prefix="/api/collaboration", tags=["collaboration"])
app.include_router(dynamic_collaborate.router, prefix="/api/dynamic-collaborate", tags=["dynamic-collaboration"])
app.include_router(council.router, tags=["council"])
app.include_router(eval.router, tags=["eval"])
app.include_router(quality_analytics.router, prefix="/api/analytics", tags=["quality-analytics"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Cross-LLM Thread Hub"}


@app.get("/health")
async def health():
    """Basic health check."""
    return {"status": "healthy", "timestamp": __import__("time").time()}


@app.get("/health/ready")
async def readiness_check():
    """
    Readiness check - verifies database connection.
    Returns 200 if ready to accept traffic, otherwise 503.
    """
    from app.database import get_db
    from sqlalchemy import text

    checks = {"database": False}

    try:
        # Create a session from the async engine
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            checks["database"] = True
    except Exception as e:
        logger.warning(f"Database readiness check failed: {e}")

    all_ok = all(checks.values())
    status_code = 200 if all_ok else 503

    return {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks
    }


@app.get("/health/live")
async def liveness_check():
    """
    Liveness check - verifies the service is running.
    This is a fast check that doesn't validate dependencies.
    """
    return {"status": "alive", "timestamp": __import__("time").time()}


if __name__ == "__main__":
    import uvicorn

    # SECURITY: Never enable reload in production
    # Code reloading exposes source code and enables remote code execution
    enable_reload = os.getenv("ENABLE_RELOAD", "false").lower() == "true"
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production" and enable_reload:
        logger.critical("⚠️ SECURITY: Code reload disabled in production mode")
        enable_reload = False

    logger.info(f"Starting Syntra API server (reload={enable_reload}, env={environment})")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=enable_reload,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
