"""Simplified FastAPI application with basic functionality."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from current directory
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Syntra API",
    description="Intelligent LLM Routing Platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatMessage(BaseModel):
    content: str
    role: str = "user"

class ChatRequest(BaseModel):
    message: str
    thread_id: str = None
    provider: str = "openai"

class ChatResponse(BaseModel):
    content: str
    provider: str
    thread_id: str
    tokens_used: int = 0

class ClerkAuthRequest(BaseModel):
    clerk_token: str
    email: str

class AuthResponse(BaseModel):
    access_token: str
    org_id: str
    user_id: str
    email: str

class CreateThreadRequest(BaseModel):
    title: str = None
    description: str = ""
    user_id: str = None

class CreateThreadResponse(BaseModel):
    thread_id: str
    created_at: str

@app.get("/")
async def root():
    return {"status": "ok", "service": "syntra-api"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "connected",
        "services": {
            "postgres": "healthy", 
            "redis": "healthy",
            "qdrant": "healthy"
        },
        "version": "1.0.0"
    }

@app.get("/api/providers")
async def get_providers():
    """Get available LLM providers."""
    return {
        "providers": [
            {
                "id": "openai",
                "name": "OpenAI GPT",
                "models": ["gpt-4", "gpt-3.5-turbo"],
                "status": "available"
            },
            {
                "id": "anthropic",
                "name": "Anthropic Claude",
                "models": ["claude-3-sonnet", "claude-3-haiku"],
                "status": "available"
            },
            {
                "id": "google",
                "name": "Google Gemini",
                "models": ["gemini-pro", "gemini-pro-vision"],
                "status": "available"
            }
        ]
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Basic chat endpoint for testing."""
    try:
        # Simulate a response - in full version this would route to actual LLM providers
        response_content = f"Hello! I received your message: '{request.message}'. This is a simplified response from the {request.provider} provider."
        
        return ChatResponse(
            content=response_content,
            provider=request.provider,
            thread_id=request.thread_id or "thread_123",
            tokens_used=len(request.message.split()) * 2  # Simple token estimate
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/threads")
async def get_threads():
    """Get user threads."""
    return {
        "threads": [
            {
                "id": "thread_123",
                "title": "Sample Conversation",
                "created_at": "2025-12-23T00:00:00Z",
                "updated_at": "2025-12-23T00:00:00Z",
                "message_count": 5
            }
        ]
    }

@app.post("/api/threads", response_model=CreateThreadResponse)
async def create_thread(request: CreateThreadRequest):
    """Create a new thread."""
    import uuid
    from datetime import datetime
    
    # Generate a unique thread ID
    thread_id = f"thread_{str(uuid.uuid4())[:8]}"
    created_at = datetime.utcnow().isoformat() + "Z"
    
    logger.info(f"Creating new thread: {thread_id} with title: {request.title}")
    
    return CreateThreadResponse(
        thread_id=thread_id,
        created_at=created_at
    )

@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str):
    """Get thread details."""
    return {
        "thread": {
            "id": thread_id,
            "title": f"Thread {thread_id}",
            "messages": [
                {
                    "id": "msg_1",
                    "role": "user",
                    "content": "Hello, how are you?",
                    "timestamp": "2025-12-23T00:00:00Z"
                },
                {
                    "id": "msg_2", 
                    "role": "assistant",
                    "content": "Hello! I'm doing well, thank you for asking. How can I help you today?",
                    "timestamp": "2025-12-23T00:00:01Z"
                }
            ]
        }
    }

@app.post("/api/auth/clerk", response_model=AuthResponse)
async def clerk_auth_endpoint(request: ClerkAuthRequest):
    """Exchange Clerk token for backend JWT token."""
    try:
        # In a real implementation, you would:
        # 1. Verify the Clerk token
        # 2. Extract user info from Clerk
        # 3. Create/update user in your database
        # 4. Generate your own JWT token
        
        # For simplified version, just return a mock response
        import uuid
        import time
        
        # Generate a mock JWT token
        mock_access_token = f"syntra_token_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        return AuthResponse(
            access_token=mock_access_token,
            org_id="org_demo",
            user_id="user_demo_123",
            email=request.email
        )
    except Exception as e:
        logger.error(f"Clerk auth error: {e}")
        raise HTTPException(status_code=400, detail="Failed to authenticate with Clerk")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Syntra API (Simplified)...")
    uvicorn.run(app, host="0.0.0.0", port=8000)