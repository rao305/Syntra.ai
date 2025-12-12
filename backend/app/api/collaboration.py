"""
Collaboration API endpoints

Dedicated endpoints for multi-agent collaboration functionality,
including follow-up questions and meta-queries about the collaboration process.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.database import get_db
from app.security import set_rls_context
from app.api.deps import require_org_id
from app.services.provider_keys import get_api_key_for_org
from app.models.provider_key import ProviderType
from app.services.main_assistant import main_assistant
from app.services.conversation_storage import ConversationStorageService, ConversationContextManager
from app.services.collaboration_engine import AgentRole
from app.services.collaboration_service import CollaborationService


router = APIRouter()
logger = logging.getLogger(__name__)


class CollaborationRequest(BaseModel):
    """Request for multi-agent collaboration"""
    user_id: Optional[str] = None
    message: str = Field(..., description="User's message or question")
    thread_id: Optional[str] = Field(None, description="Thread ID for context")


class EnhancedCollaborationRequest(BaseModel):
    """Request for enhanced multi-model collaboration"""
    user_id: Optional[str] = None
    message: str = Field(..., description="User's message or question")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    enable_external_review: bool = Field(True, description="Whether to run external review")
    review_mode: str = Field("auto", description="Review mode: auto, high_fidelity, expert")


class ThreadCollaborateRequest(BaseModel):
    """Request for thread collaboration matching frontend API contract"""
    message: str = Field(..., description="The new user message")
    mode: str = Field("auto", description="Collaboration mode: auto or manual")


class ResumeCollaborationRequest(BaseModel):
    """Request to resume a paused collaboration"""
    action: str = Field(..., description="User action: accept, edit, or cancel")
    edited_draft: Optional[str] = Field(None, description="Edited draft content (for edit action)")


class MetaQuestionRequest(BaseModel):
    """Request for meta-questions about collaboration"""
    user_id: Optional[str] = None
    question: str = Field(..., description="Meta-question about the collaboration process")
    thread_id: str = Field(..., description="Thread ID to reference")
    turn_id: Optional[str] = Field(None, description="Specific turn ID to reference")


class AgentOutputResponse(BaseModel):
    """Agent output for API responses"""
    role: str
    provider: str
    content: str
    timestamp: datetime
    turn_id: str


class CollaborationStatsResponse(BaseModel):
    """Collaboration statistics"""
    total_turns: int
    avg_time_ms: float
    mode_distribution: Dict[str, int]
    agent_role_distribution: Dict[str, int]
    total_agent_outputs: int


@router.post("/collaborate")
async def collaborate(
    request: CollaborationRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Run multi-agent collaboration on a user message.
    
    This endpoint triggers the full 5-agent collaboration pipeline:
    1. Analyst (Gemini) - Problem breakdown and structure
    2. Researcher (Perplexity) - Web research and citations
    3. Creator (GPT) - Main solution draft
    4. Critic (GPT) - Flaws and improvement suggestions  
    5. Synthesizer (GPT) - Final integrated report
    """
    await set_rls_context(db, org_id)
    
    # Collect API keys for all providers
    api_keys = {}
    for provider in [ProviderType.OPENAI, ProviderType.GEMINI, ProviderType.PERPLEXITY, ProviderType.KIMI]:
        try:
            key = await get_api_key_for_org(db, org_id, provider)
            if key:
                api_keys[provider.value] = key
        except Exception:
            continue  # Skip if provider not configured
    
    if not api_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No API keys configured for collaboration providers"
        )
    
    # Generate unique turn ID
    import uuid
    turn_id = str(uuid.uuid4())
    
    # Get chat history if thread_id provided
    chat_history = []
    if request.thread_id:
        storage_service = ConversationStorageService(db)
        stored_turns = storage_service.get_thread_history(request.thread_id)
        # Convert to simple format for main_assistant
        for turn in stored_turns:
            chat_history.extend([
                {"role": "user", "content": turn.user_query},
                {"role": "assistant", "content": turn.final_report}
            ])
    
    # Run collaboration
    result = await main_assistant.handle_message(
        user_message=request.message,
        turn_id=turn_id,
        api_keys=api_keys,
        collaboration_mode=True,
        chat_history=chat_history
    )
    
    # Store collaboration results
    if result.get("type") == "collaboration" and result.get("agent_outputs"):
        storage_service = ConversationStorageService(db)
        
        # Convert agent outputs back to AgentOutput objects for storage
        from app.services.collaboration_engine import AgentOutput, AgentRole
        agent_outputs = []
        for output_dict in result["agent_outputs"]:
            agent_outputs.append(AgentOutput(
                role=AgentRole(output_dict["role"]),
                provider=output_dict["provider"],
                content=output_dict["content"],
                timestamp=output_dict["timestamp"],
                turn_id=turn_id
            ))
        
        storage_service.store_collaboration_turn(
            turn_id=turn_id,
            thread_id=request.thread_id or f"collab_{turn_id}",
            user_query=request.message,
            final_report=result["content"],
            agent_outputs=agent_outputs,
            total_time_ms=result.get("total_time_ms", 0),
            collaboration_mode="full"
        )
    
    return {
        "final_report": result["content"],
        "turn_id": turn_id,
        "agent_outputs": [
            AgentOutputResponse(
                role=output["role"],
                provider=output["provider"], 
                content=output["content"],
                timestamp=datetime.fromtimestamp(output["timestamp"]),
                turn_id=output.get("turn_id", turn_id)
            )
            for output in result.get("agent_outputs", [])
        ],
        "total_time_ms": result.get("total_time_ms", 0),
        "type": result.get("type", "collaboration")
    }


@router.post("/meta-question")
async def ask_meta_question(
    request: MetaQuestionRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Ask meta-questions about previous collaboration turns.
    
    Examples:
    - "What did the Researcher find in my last query?"
    - "What were the Critic's concerns about the solution?"
    - "Show me what the Analyst concluded about the problem structure"
    """
    await set_rls_context(db, org_id)
    
    # Get API key for OpenAI (used for meta-question processing)
    api_keys = {}
    try:
        openai_key = await get_api_key_for_org(db, org_id, ProviderType.OPENAI)
        if openai_key:
            api_keys[ProviderType.OPENAI.value] = openai_key
    except Exception:
        pass
    
    if not api_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenAI API key required for meta-question processing"
        )
    
    # Generate unique turn ID for this meta-question
    import uuid
    turn_id = str(uuid.uuid4())
    
    # Handle meta-question
    result = await main_assistant.handle_message(
        user_message=request.question,
        turn_id=turn_id,
        api_keys=api_keys,
        collaboration_mode=False,  # Meta-questions don't need full collaboration
        chat_history=[]  # Meta-questions use stored context instead
    )
    
    return {
        "answer": result["content"],
        "turn_id": turn_id,
        "type": result.get("type", "meta_response"),
        "referenced_outputs": result.get("referenced_outputs", 0)
    }


@router.get("/threads/{thread_id}/agent-outputs")
async def get_agent_outputs(
    thread_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
    role: Optional[str] = None,
    limit: int = 20
):
    """Get agent outputs for a specific thread, optionally filtered by role"""
    await set_rls_context(db, org_id)
    
    storage_service = ConversationStorageService(db)
    
    if role:
        try:
            agent_role = AgentRole(role)
            outputs = storage_service.search_agent_outputs(
                agent_role=agent_role,
                limit=limit
            )
            # Filter by thread_id
            outputs = [o for o in outputs if o.turn.thread_id == thread_id]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid agent role: {role}"
            )
    else:
        outputs = storage_service.get_recent_outputs_for_thread(thread_id, limit)
    
    return [
        AgentOutputResponse(
            role=output.agent_role,
            provider=output.provider,
            content=output.content,
            timestamp=output.timestamp,
            turn_id=output.turn_id
        )
        for output in outputs
    ]


@router.get("/turns/{turn_id}")
async def get_collaboration_turn(
    turn_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific collaboration turn with all agent outputs"""
    await set_rls_context(db, org_id)
    
    storage_service = ConversationStorageService(db)
    
    turn = storage_service.get_turn_by_id(turn_id)
    if not turn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collaboration turn {turn_id} not found"
        )
    
    agent_outputs = storage_service.get_all_outputs_for_turn(turn_id)
    
    return {
        "turn_id": turn.turn_id,
        "thread_id": turn.thread_id,
        "user_query": turn.user_query,
        "final_report": turn.final_report,
        "collaboration_mode": turn.collaboration_mode,
        "total_time_ms": turn.total_time_ms,
        "created_at": turn.created_at,
        "agent_outputs": [
            AgentOutputResponse(
                role=output.agent_role,
                provider=output.provider,
                content=output.content,
                timestamp=output.timestamp,
                turn_id=output.turn_id
            )
            for output in agent_outputs
        ]
    }


@router.get("/threads/{thread_id}/stats")
async def get_collaboration_stats(
    thread_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """Get collaboration statistics for a specific thread"""
    await set_rls_context(db, org_id)
    
    storage_service = ConversationStorageService(db)
    stats = storage_service.get_collaboration_stats(thread_id)
    
    return CollaborationStatsResponse(**stats)


@router.get("/stats")
async def get_global_collaboration_stats(
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """Get global collaboration statistics across all threads"""
    await set_rls_context(db, org_id)
    
    storage_service = ConversationStorageService(db)
    stats = storage_service.get_collaboration_stats()
    
    return CollaborationStatsResponse(**stats)


@router.post("/follow-up")
async def ask_follow_up_question(
    request: CollaborationRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Ask follow-up questions that reference previous collaboration output.
    
    Examples:
    - "In the solution architecture, can you expand the roadmap?"
    - "Explain more details about the security considerations"
    - "Dive deeper into the performance optimization section"
    """
    await set_rls_context(db, org_id)
    
    if not request.thread_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="thread_id is required for follow-up questions"
        )
    
    # Get API key for OpenAI (used for follow-up processing)
    api_keys = {}
    try:
        openai_key = await get_api_key_for_org(db, org_id, ProviderType.OPENAI)
        if openai_key:
            api_keys[ProviderType.OPENAI.value] = openai_key
    except Exception:
        pass
    
    if not api_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenAI API key required for follow-up question processing"
        )
    
    # Generate unique turn ID
    import uuid
    turn_id = str(uuid.uuid4())
    
    # Handle follow-up question
    result = await main_assistant.handle_message(
        user_message=request.message,
        turn_id=turn_id,
        api_keys=api_keys,
        collaboration_mode=False,  # Follow-ups use previous context
        chat_history=[]  # Follow-ups use stored context instead
    )
    
    return {
        "answer": result["content"],
        "turn_id": turn_id,
        "type": result.get("type", "followup_response"),
        "referenced_report": result.get("referenced_report")
    }


@router.post("/enhanced")
async def enhanced_collaborate(
    request: EnhancedCollaborationRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Enhanced multi-model collaboration with external review and meta-synthesis.
    
    This endpoint uses the new pipeline:
    1. Internal team collaboration (5 stages)
    2. Report compression 
    3. External multi-model review (optional)
    4. Meta-synthesis final answer
    """
    await set_rls_context(db, org_id)
    
    # Get all available API keys
    api_keys = {}
    provider_types = [
        ProviderType.OPENAI,
        ProviderType.GEMINI,
        ProviderType.PERPLEXITY,
        ProviderType.KIMI,
        ProviderType.OPENROUTER
    ]
    
    for provider_type in provider_types:
        try:
            key = await get_api_key_for_org(db, org_id, provider_type)
            if key:
                api_keys[provider_type.value] = key
        except Exception:
            continue
    
    if not api_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one API key required for enhanced collaboration"
        )
    
    # Initialize collaboration service
    collab_service = CollaborationService(db, org_id)
    
    # Create or get conversation
    conversation_id = request.conversation_id
    if not conversation_id:
        conversation = await collab_service.create_conversation(
            org_id=org_id,
            user_id=request.user_id,
            title=f"Enhanced Collaboration: {request.message[:50]}..."
        )
        conversation_id = str(conversation.id)
    
    # Start enhanced collaboration
    try:
        result = await collab_service.start_collaboration(
            conversation_id=conversation_id,
            user_message=request.message,
            api_keys=api_keys,
            enable_external_review=request.enable_external_review,
            review_mode=request.review_mode
        )
        
        # Format response for frontend
        return {
            "collab_run": {
                "id": str(result["collab_run"].id),
                "conversation_id": str(result["collab_run"].conversation_id),
                "status": result["collab_run"].status.value,
                "total_time_ms": result["total_time_ms"]
            },
            "internal_report": result["internal_report"],
            "compressed_report": result["compressed_report"],
            "external_critiques": result["external_critiques"],
            "final_answer": result["final_answer"],
            "synthesis_metadata": result["synthesis_metadata"],
            "external_review_conducted": result["external_review_conducted"],
            "reviewers_consulted": result["reviewers_consulted"],
            "total_time_ms": result["total_time_ms"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enhanced collaboration failed: {str(e)}"
        )


@router.get("/info")
async def get_collaboration_info(
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """Get information about available collaboration options."""
    await set_rls_context(db, org_id)
    
    # Check which providers have API keys configured
    available_providers = []
    provider_types = [
        ProviderType.OPENAI,
        ProviderType.GEMINI, 
        ProviderType.PERPLEXITY,
        ProviderType.KIMI,
        ProviderType.OPENROUTER
    ]
    
    for provider_type in provider_types:
        try:
            key = await get_api_key_for_org(db, org_id, provider_type)
            if key:
                available_providers.append(provider_type.value)
        except Exception:
            continue
    
    return {
        "available_providers": available_providers,
        "review_modes": [
            {
                "mode": "auto",
                "name": "Auto", 
                "description": "External review triggered automatically based on confidence"
            },
            {
                "mode": "high_fidelity",
                "name": "High Fidelity",
                "description": "Always include external multi-model review"
            },
            {
                "mode": "expert", 
                "name": "Expert",
                "description": "Maximum external reviewers + comprehensive analysis"
            }
        ],
        "default_settings": {
            "enable_external_review": True,
            "review_mode": "auto"
        }
    }


@router.post("/{thread_id}/collaborate")
async def thread_collaborate(
    thread_id: str,
    request: ThreadCollaborateRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Enhanced collaboration endpoint for threads matching frontend API contract.
    
    This endpoint:
    - POST /api/threads/:threadId/collaborate
    - Returns structured response with internal_pipeline + external_reviews + final_answer
    - Matches the exact TypeScript interface expected by frontend
    """
    await set_rls_context(db, org_id)
    
    # Import the transformer here to avoid circular imports
    from app.services.collaborate_response_transformer import transform_enhanced_collaboration_response
    
    # Get all available API keys
    api_keys = {}
    provider_types = [
        ProviderType.OPENAI,
        ProviderType.GEMINI,
        ProviderType.PERPLEXITY,
        ProviderType.KIMI,
        ProviderType.OPENROUTER
    ]
    
    for provider_type in provider_types:
        try:
            key = await get_api_key_for_org(db, org_id, provider_type)
            if key:
                api_keys[provider_type.value] = key
        except Exception:
            continue
    
    if not api_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one API key required for collaboration"
        )
    
    # Initialize collaboration service
    collab_service = CollaborationService(db, org_id)
    
    # Use thread_id as conversation_id
    conversation_id = thread_id
    
    try:
        # Check if conversation exists, if not create it
        conversation = await collab_service.get_conversation(conversation_id)
        if not conversation:
            conversation = await collab_service.create_conversation(
                org_id=org_id,
                user_id=None,  # Thread-based collaboration doesn't need user_id
                title=f"Thread {thread_id} Collaboration"
            )
            conversation_id = str(conversation.id)
        
        # Map mode to external review settings
        enable_external_review = True  # Always enable for better results
        review_mode = "auto"  # Smart mode by default
        
        if request.mode == "manual":
            # Manual mode could use high_fidelity for more thorough review
            review_mode = "high_fidelity"
        
        # Start enhanced collaboration
        enhanced_result = await collab_service.start_collaboration(
            conversation_id=conversation_id,
            user_message=request.message,
            api_keys=api_keys,
            enable_external_review=enable_external_review,
            review_mode=review_mode
        )
        
        # Transform to API contract format
        api_response = transform_enhanced_collaboration_response(enhanced_result)
        
        return api_response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Thread collaboration failed: {str(e)}"
        )


@router.post("/{thread_id}/collaborate/stream")
async def thread_collaborate_stream(
    thread_id: str,
    request: ThreadCollaborateRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Enhanced collaboration endpoint with Server-Sent Events streaming.
    
    This endpoint streams stage events in real-time:
    - stage_start: When each collaboration stage begins
    - stage_end: When each stage completes  
    - final_chunk: Chunks of the final answer as it's generated
    - done: Final message when collaboration is complete
    """
    from fastapi.responses import StreamingResponse
    import json
    import asyncio
    
    await set_rls_context(db, org_id)
    
    def sse_event(data: dict) -> str:
        """Format data as Server-Sent Events"""
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    
    async def event_generator():
        """Generate SSE events for collaboration stages"""
        try:
            # Get all available API keys
            api_keys = {}
            provider_types = [
                ProviderType.OPENAI,
                ProviderType.GEMINI,
                ProviderType.PERPLEXITY,
                ProviderType.KIMI,
                ProviderType.OPENROUTER
            ]
            
            for provider_type in provider_types:
                try:
                    key = await get_api_key_for_org(db, org_id, provider_type)
                    if key:
                        api_keys[provider_type.value] = key
                except Exception as e:
                    # Rollback transaction on DB error to prevent InFailedSQLTransactionError
                    try:
                        await db.rollback()
                    except Exception:
                        pass
                    continue
            
            if not api_keys:
                yield sse_event({
                    "type": "error",
                    "message": "At least one API key required for collaboration"
                })
                return
            
            # Initialize collaboration service
            collab_service = CollaborationService(db, org_id)
            conversation_id = thread_id
            
            # For now, skip conversation lookup for testing
            # This allows testing without the collaboration tables migration
            try:
                conversation = await collab_service.get_conversation(conversation_id)
                if not conversation:
                    conversation = await collab_service.create_conversation(
                        org_id=org_id,
                        user_id=None,
                        title=f"Thread {thread_id} Collaboration"
                    )
                    conversation_id = str(conversation.id)
            except Exception as e:
                logger.warning(f"Skipping conversation lookup for testing: {e}")
                # CRITICAL: Rollback the aborted transaction before continuing
                # Without this, all subsequent DB queries fail with InFailedSQLTransactionError
                try:
                    await db.rollback()
                except Exception:
                    pass
                # Use thread_id as conversation_id for testing
                pass
            
            # Save user message to database first to maintain context
            from app.models.message import Message, MessageRole
            from sqlalchemy import select, func

            chat_history = []
            assistant_sequence = 0

            try:
                # Get next sequence number
                sequence_stmt = select(func.max(Message.sequence)).where(Message.thread_id == thread_id)
                sequence_result = await db.execute(sequence_stmt)
                max_sequence = sequence_result.scalar()
                next_sequence = (max_sequence or -1) + 1

                # Create and save user message
                user_message = Message(
                    thread_id=thread_id,
                    role=MessageRole.USER,
                    content=request.message,
                    sequence=next_sequence,
                )
                db.add(user_message)
                await db.flush()
                await db.refresh(user_message)

                # Load thread history for context (including the user message we just saved)
                MAX_CONTEXT_MESSAGES = 20
                history_stmt = (
                    select(Message)
                    .where(Message.thread_id == thread_id)
                    .order_by(Message.sequence.desc())
                    .limit(MAX_CONTEXT_MESSAGES)
                )
                history_result = await db.execute(history_stmt)
                prior_messages = list(history_result.scalars().all())
                prior_messages.reverse()  # Reverse to get chronological order
                chat_history = [
                    {"role": msg.role.value, "content": msg.content}
                    for msg in prior_messages
                ]

                # Commit user message before starting collaboration
                await db.commit()

                # Calculate assistant sequence right after commit while transaction is fresh
                assistant_sequence = next_sequence + 1

            except Exception as e:
                logger.error(f"Error saving user message: {e}", exc_info=True)
                try:
                    await db.rollback()
                except Exception:
                    pass

                # Yield error and return
                yield sse_event({
                    "type": "error",
                    "message": f"Failed to save user message: {str(e)}"
                })
                return

            # Initialize the real collaboration orchestrator
            from app.services.collaboration_orchestrator import CollaborationOrchestrator
            orchestrator = CollaborationOrchestrator(db)

            # Track the final answer for message creation
            final_answer_parts = []
            enhanced_result = None
            pipeline_data = None
            
            # Stream real collaboration events with chat history
            try:
                async for event in orchestrator.run_collaboration_stream(
                    thread_id=thread_id,
                    user_message=request.message,
                    api_keys=api_keys,
                    mode=request.mode,
                    chat_history=chat_history
                ):
                    if event["type"] == "final_chunk":
                        # Collect chunks for final message
                        final_answer_parts.append(event["text"])
                    elif event["type"] == "done":
                        # Store the final result metadata and pipeline data
                        enhanced_result = event.get("result")
                        pipeline_data = event.get("pipeline_data")

                    # Forward all events to client
                    yield sse_event(event)
            except Exception as stream_error:
                # Log the streaming error and rollback transaction
                logger.error(f"Error during collaboration streaming: {stream_error}", exc_info=True)
                try:
                    await db.rollback()
                except Exception:
                    pass
                # Yield error event to client
                yield sse_event({
                    "type": "error",
                    "message": f"Collaboration stream error: {str(stream_error)}"
                })
                return
            
            # Reconstruct final answer from chunks
            if final_answer_parts:
                final_answer = "".join(final_answer_parts)
            elif enhanced_result:
                final_answer = enhanced_result.get("final_answer", "")
            else:
                # Stream failed before producing any output
                final_answer = ""

            # Send completion event with full message data
            from app.models.message import Message, MessageRole

            # Note: assistant_sequence was already calculated before streaming
            final_message = None

            try:
                # Create and save the final message
                final_message = Message(
                    thread_id=thread_id,
                    role=MessageRole.ASSISTANT,
                    content=final_answer,
                    provider="collaborate",
                    model="multi-model",
                    meta={
                        "engine": "collaborate",
                        "collaborate": {
                            "mode": request.mode,
                            "stages_completed": enhanced_result.get("stages_completed", 6) if enhanced_result else 6,
                            "external_reviews_count": enhanced_result.get("external_reviews_count", 0) if enhanced_result else 0,
                            "confidence_level": "high",
                            "duration_ms": enhanced_result.get("duration_ms", 0) if enhanced_result else 0
                        }
                    },
                    sequence=assistant_sequence
                )

                # Save the collaboration message to database with proper meta
                db.add(final_message)
                await db.commit()
                await db.refresh(final_message)
                logger.info(f"✅ Saved collaboration message {final_message.id} to database")

            except Exception as e:
                logger.error(f"Failed to save collaboration message: {e}", exc_info=True)
                try:
                    await db.rollback()
                except Exception:
                    pass

                # Create a temporary message object for response (not persisted)
                final_message = Message(
                    thread_id=thread_id,
                    role=MessageRole.ASSISTANT,
                    content=final_answer,
                    provider="collaborate",
                    model="multi-model",
                    sequence=assistant_sequence
                )
                # Set id to None to indicate it wasn't persisted
                final_message.id = None
            
            # Include pipeline data from the done event if available
            pipeline_data = None
            if enhanced_result and "pipeline_data" in enhanced_result:
                pipeline_data = enhanced_result["pipeline_data"]
            
            # Prepare final message response
            final_response = {
                "type": "done",
                "message": {
                    "id": str(final_message.id) if final_message.id else "pending",
                    "thread_id": thread_id,
                    "role": final_message.role.value,
                    "content": final_message.content,
                    "created_at": final_message.created_at.isoformat() if hasattr(final_message, 'created_at') and final_message.created_at else datetime.utcnow().isoformat(),
                    "provider": final_message.provider,
                    "model": final_message.model,
                    "meta": final_message.meta,
                    "saved": final_message.id is not None  # Indicate if message was persisted
                },
                "pipeline_data": pipeline_data
            }

            yield sse_event(final_response)
            
        except Exception as e:
            yield sse_event({
                "type": "error", 
                "message": f"Collaboration streaming failed: {str(e)}"
            })
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/{run_id}/resume")
async def resume_collaboration_stream(
    run_id: str,
    request: ResumeCollaborationRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Resume a paused collaboration from manual mode.
    
    This endpoint is called after user reviews the draft in manual mode.
    It continues the collaboration pipeline from the critic stage onwards.
    """
    from fastapi.responses import StreamingResponse
    import json
    import asyncio
    
    await set_rls_context(db, org_id)
    
    def sse_event(data: dict) -> str:
        """Format data as Server-Sent Events"""
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    
    async def event_generator():
        """Generate SSE events for resumed collaboration"""
        try:
            # Get API keys
            api_keys = {}
            provider_types = [
                ProviderType.OPENAI,
                ProviderType.GEMINI,
                ProviderType.PERPLEXITY,
                ProviderType.KIMI,
                ProviderType.OPENROUTER
            ]
            
            for provider_type in provider_types:
                try:
                    key = await get_api_key_for_org(db, org_id, provider_type)
                    if key:
                        api_keys[provider_type.value] = key
                except Exception as e:
                    # Rollback transaction on DB error to prevent InFailedSQLTransactionError
                    try:
                        await db.rollback()
                    except Exception:
                        pass
                    continue
            
            if not api_keys:
                yield sse_event({
                    "type": "error",
                    "message": "At least one API key required for collaboration"
                })
                return
            
            # Initialize orchestrator and resume
            from app.services.collaboration_orchestrator import CollaborationOrchestrator
            orchestrator = CollaborationOrchestrator(db)
            
            # Track final answer parts and result
            final_answer_parts = []
            enhanced_result = None
            
            # Stream resumed collaboration events
            async for event in orchestrator.resume_collaboration_stream(
                run_id=run_id,
                user_action=request.action,
                edited_draft=request.edited_draft,
                api_keys=api_keys
            ):
                if event["type"] == "final_chunk":
                    # Collect chunks for final message
                    final_answer_parts.append(event["text"])
                elif event["type"] == "done":
                    # Store the final result metadata
                    enhanced_result = event["result"]
                
                # Forward all events to client
                yield sse_event(event)
            
            # If collaboration was cancelled, don't create a message
            if enhanced_result and enhanced_result.get("cancelled"):
                return
            
            # Reconstruct final answer from chunks
            if final_answer_parts:
                final_answer = "".join(final_answer_parts)
            elif enhanced_result:
                final_answer = enhanced_result.get("final_answer", "")
            else:
                # Stream failed before producing any output
                final_answer = ""
            
            # Create and save the final message for completed collaborations
            if final_answer and enhanced_result:
                from app.models.message import Message, MessageRole
                
                # Get the thread_id from the collaboration run
                # For now, we'll extract it from the run_id or use a placeholder
                thread_id = f"thread_{run_id}"  # This should be stored in the run record
                
                final_message = Message(
                    thread_id=thread_id,
                    role=MessageRole.ASSISTANT,
                    content=final_answer,
                    provider="collaborate",
                    model="multi-model",
                    meta={
                        "engine": "collaborate",
                        "collaborate": {
                            "mode": "manual",
                            "run_id": run_id,
                            "stages_completed": enhanced_result.get("stages_completed", 6),
                            "external_reviews_count": enhanced_result.get("external_reviews_count", 0),
                            "confidence_level": "high",
                            "duration_ms": enhanced_result.get("duration_ms", 0),
                            "user_action": request.action
                        }
                    },
                    sequence=1
                )
                
                try:
                    db.add(final_message)
                    await db.commit()
                    await db.refresh(final_message)
                    
                    yield sse_event({
                        "type": "message_saved",
                        "message": {
                            "id": str(final_message.id),
                            "thread_id": thread_id,
                            "role": final_message.role.value,
                            "content": final_message.content,
                            "created_at": final_message.created_at.isoformat() if hasattr(final_message, 'created_at') and final_message.created_at else datetime.utcnow().isoformat(),
                            "provider": final_message.provider,
                            "model": final_message.model,
                            "meta": final_message.meta
                        }
                    })
                    
                except Exception as e:
                    print(f"❌ Failed to save resumed collaboration message: {e}")
                    await db.rollback()
            
        except Exception as e:
            yield sse_event({
                "type": "error",
                "message": f"Resume collaboration failed: {str(e)}"
            })
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )