"""FastAPI application entry point."""
from fastapi import FastAPI

app = FastAPI(
    title="Cross-LLM Thread Hub API",
    description="Multi-tenant B2B hub for cross-provider conversation threading",
    version="0.1.0"
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}

