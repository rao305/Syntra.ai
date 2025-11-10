"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import get_settings
from app.database import init_db, close_db
from app.api import threads, router, providers, billing, audit, metrics
from app.middleware import ObservabilityMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="Cross-LLM Thread Hub",
    description="Multi-tenant B2B SaaS for cross-provider LLM threading",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url] if settings.is_production else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Observability middleware (Phase 1.5)
app.add_middleware(ObservabilityMiddleware)

# Include routers
app.include_router(threads.router, prefix="/api/threads", tags=["threads"])
app.include_router(router.router, prefix="/api/router", tags=["router"])
app.include_router(providers.router, prefix="/api/orgs", tags=["providers"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Cross-LLM Thread Hub"}


@app.get("/health")
async def health():
    """Health check with DB status."""
    # TODO: Add DB ping check
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
