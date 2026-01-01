"""Minimal FastAPI application for testing."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Syntra API (Minimal)",
    description="Minimal Syntra API for testing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "service": "syntra-api-minimal"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "connected",
        "services": {
            "postgres": "healthy",
            "redis": "healthy",
            "qdrant": "healthy"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)