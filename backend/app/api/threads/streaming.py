"""
Server-Sent Events streaming for real-time responses.

This module handles streaming message responses to users with real-time
LLM output and proper provider information.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
import logging
import json
import time
import os

from app.database import get_db
from app.security import set_rls_context
from app.api.deps import require_org_id, get_current_user_optional, CurrentUser
from app.core.exceptions import handle_exceptions
from config import get_settings
from app.models.message import Message, MessageRole
from app.models.provider_key import ProviderType
from .schemas import AddMessageRequest
from app.services.provider_keys import get_api_key_for_org

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("/{thread_id}/messages/stream")
async def add_message_streaming(
    thread_id: str,
    request: AddMessageRequest,
    org_id: str = Depends(require_org_id),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Stream a message response using SSE with real LLM calls."""
    logger.info(f"Streaming message to thread {thread_id[:8]} for org {org_id[:8]}")

    user_id = current_user.id if current_user else None
    await set_rls_context(db, org_id, user_id)

    # Determine provider - default to openai for now
    provider_str = getattr(request, 'provider', None) or 'openai'
    if isinstance(provider_str, ProviderType):
        provider_enum = provider_str
    else:
        try:
            provider_enum = ProviderType(str(provider_str).lower())
        except ValueError:
            provider_enum = ProviderType.OPENAI

    model = getattr(request, 'model', None) or 'gpt-4o-mini'
    reason = getattr(request, 'reason', None) or 'Default model'

    logger.info(f"Using provider: {provider_enum.value}, model: {model}")

    # Get API key
    api_key = None

    # Try environment variables first
    if provider_enum == ProviderType.OPENAI:
        api_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
    elif provider_enum == ProviderType.GEMINI:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or settings.google_api_key
    elif provider_enum == ProviderType.PERPLEXITY:
        api_key = os.getenv("PERPLEXITY_API_KEY") or settings.perplexity_api_key
    elif provider_enum == ProviderType.KIMI:
        api_key = os.getenv("KIMI_API_KEY")
    elif provider_enum == ProviderType.OPENROUTER:
        api_key = os.getenv("OPENROUTER_API_KEY") or settings.openrouter_api_key

    # Fallback to database
    if not api_key:
        try:
            api_key = await get_api_key_for_org(db, org_id, provider_enum)
        except Exception:
            logger.warning(f"Could not get API key for {provider_enum.value}")

    # Build messages for provider
    messages = []

    # Add system prompt
    messages.append({
        "role": "system",
        "content": "You are a helpful AI assistant."
    })

    # Get conversation history
    try:
        history_result = await db.execute(
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.created_at.asc())
            .limit(20)
        )
        history_messages = history_result.scalars().all()
        for msg in history_messages:
            messages.append({
                "role": msg.role.value if hasattr(msg.role, 'value') else str(msg.role).lower(),
                "content": msg.content
            })
    except Exception as e:
        logger.warning(f"Could not retrieve history: {e}")

    # Add current user message
    messages.append({
        "role": "user",
        "content": request.content
    })

    logger.info(f"Built {len(messages)} messages for provider")

    # CRITICAL: Save user message BEFORE streaming starts
    user_message_saved = False
    user_sequence = None
    try:
        # Get next sequence number
        seq_result = await db.execute(
            select(func.max(Message.sequence)).where(Message.thread_id == thread_id)
        )
        max_seq = seq_result.scalar() or 0
        user_sequence = max_seq + 1

        message_user_id = current_user.id if current_user else request.user_id
        user_msg = Message(
            thread_id=thread_id,
            user_id=message_user_id,
            role=MessageRole.USER,
            content=request.content,
            sequence=user_sequence,
        )
        db.add(user_msg)
        await db.commit()
        user_message_saved = True
        logger.info(f"💾 Saved user message to database (sequence: {user_sequence}, user_id: {message_user_id})")
        # Re-set RLS context after commit since SET LOCAL is transaction-scoped
        await set_rls_context(db, org_id, user_id)
    except Exception as e:
        logger.error(f"⚠️ Failed to save user message: {e}")
        await db.rollback()

    # Stream response
    async def event_source():
        start_time = time.perf_counter()
        ttft_emitted = False
        response_content = ""
        usage_data = {}

        # Send router info
        router_data = {
            'provider': provider_enum.value,
            'model': model,
            'reason': reason,
            'thread_id': thread_id
        }
        yield f"event: router\ndata: {json.dumps(router_data)}\n\n"

        # Send model info
        model_data = {
            "type": "model_info",
            "provider": provider_enum.value,
            "model": model,
        }
        yield f"event: model_info\ndata: {json.dumps(model_data)}\n\n"

        try:
            # Call the LLM provider adapter
            from app.services.provider_dispatch import call_provider_adapter_streaming

            stream_start = time.perf_counter()
            first_chunk = True

            async for chunk in call_provider_adapter_streaming(
                provider_enum,
                model,
                messages,
                api_key
            ):
                if first_chunk:
                    logger.info(f"🚀 First chunk in {(time.perf_counter() - stream_start)*1000:.0f}ms")
                    first_chunk = False

                chunk_type = chunk.get("type", "delta")

                # Collect response content and metadata
                if chunk_type == "delta" and "delta" in chunk:
                    response_content += chunk["delta"]
                elif chunk_type == "meta":
                    if "usage" in chunk:
                        usage_data.update(chunk["usage"])
                elif chunk_type == "done":
                    if "usage" in chunk and isinstance(chunk["usage"], dict):
                        usage_data.update(chunk["usage"])

                # Emit TTFT on first delta
                if chunk_type == "delta" and not ttft_emitted:
                    ttft_ms = int((time.perf_counter() - start_time) * 1000)
                    yield f"event: meta\ndata: {json.dumps({'type': 'meta', 'ttft_ms': ttft_ms})}\n\n"
                    ttft_emitted = True

                # Forward chunk to client
                yield f"event: {chunk_type}\ndata: {json.dumps(chunk)}\n\n"

            logger.info(f"✅ Streaming complete - {len(response_content)} chars received")

            # Save assistant message to database AFTER streaming completes
            if response_content:
                try:
                    # Get next sequence number (after user message)
                    seq_result = await db.execute(
                        select(func.max(Message.sequence)).where(Message.thread_id == thread_id)
                    )
                    max_seq = seq_result.scalar() or 0
                    assistant_sequence = max_seq + 1

                    # Create assistant message
                    message_user_id = current_user.id if current_user else request.user_id
                    assistant_msg = Message(
                        thread_id=thread_id,
                        user_id=message_user_id,
                        role=MessageRole.ASSISTANT,
                        content=response_content,
                        sequence=assistant_sequence,
                        provider=provider_enum.value,
                        model=model,
                        prompt_tokens=usage_data.get("input_tokens"),
                        completion_tokens=usage_data.get("output_tokens"),
                        meta={
                            "provider": provider_enum.value,
                            "model": model,
                            "reason": reason,
                        }
                    )
                    db.add(assistant_msg)
                    await db.commit()
                    logger.info(f"💾 Saved assistant message to database (sequence: {assistant_sequence}, user_id: {message_user_id}, thread_id: {thread_id})")
                    # Re-set RLS context after commit since SET LOCAL is transaction-scoped
                    await set_rls_context(db, org_id, user_id)
                except Exception as e:
                    logger.error(f"⚠️ Failed to save assistant message: {e}")
                    await db.rollback()

        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
