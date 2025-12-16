"""
Multi-Agent Council API Endpoints

Dedicated endpoints for the Multi-Agent Council Orchestrator,
supporting all configured LLM providers (OpenAI, Gemini, Perplexity, Kimi).
"""

import logging
import uuid
import json
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import set_rls_context
from app.api.deps import require_org_id
from app.services.provider_keys import get_api_key_for_org
from app.models.provider_key import ProviderType
from app.services.council import CouncilOrchestrator, CouncilConfig
from app.services.council.config import OutputMode

router = APIRouter(prefix="/api/council", tags=["council"])
logger = logging.getLogger(__name__)

# In-memory storage for council executions
# In production, use Redis or database
council_sessions: Dict[str, Dict[str, Any]] = {}

# In-memory storage for WebSocket connections per session
# Maps session_id -> list of connected WebSockets
session_websockets: Dict[str, list] = {}


class CouncilRequest(BaseModel):
    """Request to run Multi-Agent Council"""
    query: str = Field(..., description="The query/task for the council to analyze")
    output_mode: str = Field(
        "deliverable-ownership",
        description="Output verbosity: deliverable-only, deliverable-ownership, audit, full-transcript"
    )
    preferred_providers: Optional[Dict[str, str]] = Field(
        None,
        description="Map of agent names to preferred providers (e.g., {'architect': 'openai'})"
    )
    # Syntra SuperBenchmark features
    context_pack: Optional[Dict[str, Any]] = Field(
        None,
        description="Context pack dict with locked_decisions, glossary, open_questions, style_rules"
    )
    lexicon_lock: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Lexicon lock with 'allowed_terms' and/or 'forbidden_terms' lists"
    )
    output_contract: Optional[Dict[str, Any]] = Field(
        None,
        description="Output contract with required_headings, file_count, format constraints"
    )
    transparency_mode: bool = Field(
        False,
        description="Whether to show internal stages/models in output"
    )


class CouncilResponse(BaseModel):
    """Response from council execution"""
    session_id: str
    status: str  # "pending", "running", "success", "error"
    output: Optional[str] = None
    error: Optional[str] = None


async def broadcast_to_session(session_id: str, message: Dict[str, Any]):
    """Broadcast a message to all WebSocket clients connected to a session."""
    if session_id not in session_websockets:
        return

    disconnected = []
    for websocket in session_websockets[session_id]:
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.debug(f"Failed to send message to WebSocket: {e}")
            disconnected.append(websocket)

    # Remove disconnected WebSockets
    for ws in disconnected:
        try:
            session_websockets[session_id].remove(ws)
        except ValueError:
            pass


class CouncilProgressEvent(BaseModel):
    """Server-sent event for council progress"""
    type: str  # "phase_start", "phase_complete", "error", "complete"
    phase: Optional[str] = None
    message: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None


@router.post("/orchestrate")
async def orchestrate_council(
    request: CouncilRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
) -> CouncilResponse:
    """
    Start a Multi-Agent Council orchestration session.

    Returns immediately with a session_id for polling/WebSocket updates.

    The council runs asynchronously with three phases:
    1. Phase 1: 5 specialist agents run in parallel
    2. Phase 2: Debate Synthesizer merges outputs
    3. Phase 3: Judge Agent produces final deliverable with verdict

    Supports all configured providers: OpenAI, Gemini, Perplexity, Kimi
    """
    try:
        await set_rls_context(db, org_id)
    except Exception as e:
        logger.error(f"Error setting RLS context: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RLS context error: {str(e)}"
        )

    # Collect API keys for all providers
    api_keys = {}
    providers_checked = []
    providers_found = []
    providers_missing = []
    
    try:
        for provider in [
            ProviderType.OPENAI,
            ProviderType.GEMINI,
            ProviderType.PERPLEXITY,
            ProviderType.KIMI,
        ]:
            providers_checked.append(provider.value)
            try:
                key = await get_api_key_for_org(db, org_id, provider)
                if key:
                    api_keys[provider.value] = key
                    providers_found.append(provider.value)
                    logger.info(f"✅ API key found for {provider.value}")
                else:
                    providers_missing.append(provider.value)
                    logger.debug(f"⚠️  No API key for {provider.value}")
            except HTTPException:
                # Provider not configured (expected for some orgs)
                providers_missing.append(provider.value)
                logger.debug(f"⚠️  Provider {provider.value} not configured for org {org_id}")
            except Exception as e:
                providers_missing.append(provider.value)
                logger.warning(f"❌ Error retrieving API key for {provider.value}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error collecting API keys: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error collecting API keys: {str(e)}"
        )

    # Log summary of API key collection
    logger.info(
        f"API Key Collection Summary for org {org_id}: "
        f"Found: {providers_found}, Missing: {providers_missing}, "
        f"Total available: {len(api_keys)}/{len(providers_checked)}"
    )

    if not api_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No API keys configured. At least one provider required: openai, gemini, perplexity, or kimi"
        )

    # Create session
    session_id = str(uuid.uuid4())

    # Initialize agents with default state
    agents_state = {
        "Optimizer Agent": {"status": "pending", "duration": 0, "output": ""},
        "Red Teamer Agent": {"status": "pending", "duration": 0, "output": ""},
        "Data Engineer Agent": {"status": "pending", "duration": 0, "output": ""},
        "Researcher Agent": {"status": "pending", "duration": 0, "output": ""},
        "Architect Agent": {"status": "pending", "duration": 0, "output": ""},
        "Debate Synthesizer": {"status": "pending", "duration": 0, "output": ""},
        "Judge Agent": {"status": "pending", "duration": 0, "output": ""},
        "Final Answer": {"status": "pending", "duration": 0, "output": ""},
    }

    council_sessions[session_id] = {
        "status": "pending",
        "created_at": __import__("datetime").datetime.utcnow(),
        "output": None,
        "error": None,
        "current_phase": None,
        "execution_time_ms": None,
        "org_id": org_id,
        "agents": agents_state,
        # Store API key status for debugging
        "api_keys_status": {
            "available_providers": providers_found,
            "missing_providers": providers_missing,
            "total_providers": len(providers_found)
        }
    }

    # Parse preferred providers if specified
    preferred_providers = {}
    if request.preferred_providers:
        for agent, provider_str in request.preferred_providers.items():
            try:
                preferred_providers[agent] = ProviderType(provider_str.lower())
            except ValueError:
                logger.warning(f"Invalid provider '{provider_str}' for agent '{agent}'")

    # Start council execution in background
    import asyncio
    asyncio.create_task(
        _run_council_async(
            session_id=session_id,
            query=request.query,
            output_mode=request.output_mode,
            api_keys=api_keys,
            preferred_providers=preferred_providers,
            context_pack=request.context_pack,
            lexicon_lock=request.lexicon_lock,
            output_contract=request.output_contract,
            transparency_mode=request.transparency_mode
        )
    )

    # Log which providers will be used for this orchestration
    logger.info(
        f"Starting council orchestration for session {session_id} with providers: {list(api_keys.keys())}"
    )

    return CouncilResponse(
        session_id=session_id,
        status="pending",
        current_phase=f"Initializing... (Using providers: {', '.join(providers_found) if providers_found else 'none'})"
    )


@router.get("/orchestrate/{session_id}")
async def get_council_status(
    session_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
) -> CouncilResponse:
    """Check status of a council orchestration session."""
    await set_rls_context(db, org_id)

    if session_id not in council_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Council session not found"
        )

    session = council_sessions[session_id]

    # Verify org_id matches
    if session.get("org_id") != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized"
        )

    # Log API key status if available
    api_keys_status = session.get("api_keys_status")
    if api_keys_status:
        logger.debug(
            f"Session {session_id} API keys: {api_keys_status.get('available_providers')} available, "
            f"{api_keys_status.get('missing_providers')} missing"
        )

    return CouncilResponse(
        session_id=session_id,
        status=session["status"],
        output=session.get("output"),
        error=session.get("error"),
        execution_time_ms=session.get("execution_time_ms"),
        current_phase=session.get("current_phase")
    )


@router.get("/api-keys/status")
async def get_api_keys_status(
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check which API keys are configured for the organization.
    Useful for debugging and verifying provider connectivity.
    """
    await set_rls_context(db, org_id)
    
    providers_status = {}
    all_providers = [
        ProviderType.OPENAI,
        ProviderType.GEMINI,
        ProviderType.PERPLEXITY,
        ProviderType.KIMI,
    ]
    
    for provider in all_providers:
        try:
            key = await get_api_key_for_org(db, org_id, provider)
            providers_status[provider.value] = {
                "configured": True,
                "source": "database" if key else "environment",
                "has_key": bool(key)
            }
        except HTTPException:
            providers_status[provider.value] = {
                "configured": False,
                "source": None,
                "has_key": False
            }
        except Exception as e:
            providers_status[provider.value] = {
                "configured": False,
                "source": None,
                "has_key": False,
                "error": str(e)
            }
    
    available_count = sum(1 for p in providers_status.values() if p.get("has_key"))
    
    return {
        "org_id": org_id,
        "providers": providers_status,
        "summary": {
            "total_checked": len(all_providers),
            "available": available_count,
            "missing": len(all_providers) - available_count
        }
    }


@router.delete("/orchestrate/{session_id}")
async def cancel_council(
    session_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Cancel a running council session."""
    await set_rls_context(db, org_id)

    if session_id not in council_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Council session not found"
        )

    session = council_sessions[session_id]

    # Verify org_id matches
    if session.get("org_id") != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized"
        )

    if session["status"] in ["pending", "running"]:
        session["status"] = "cancelled"
        session["error"] = "Cancelled by user"
        return {"status": "cancelled"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel session with status '{session['status']}'"
        )


@router.websocket("/ws/{session_id}")
async def websocket_council_updates(
    websocket: WebSocket,
    session_id: str
):
    """WebSocket endpoint for real-time council progress updates."""
    await websocket.accept()

    # Register this WebSocket connection
    if session_id not in session_websockets:
        session_websockets[session_id] = []
    session_websockets[session_id].append(websocket)

    try:
        if session_id not in council_sessions:
            await websocket.send_json({
                "type": "error",
                "error": "Session not found"
            })
            await websocket.close(code=4004)
            return

        # Send initial status
        session = council_sessions[session_id]
        await websocket.send_json({
            "type": "status",
            "session_id": session_id,
            "status": session["status"],
            "created_at": session["created_at"].isoformat()
        })

        # Poll for updates
        last_phase = None
        last_agents_state = {}

        while session["status"] in ["pending", "running"]:
            import asyncio
            await asyncio.sleep(0.5)  # Check every 0.5 seconds for more responsive updates

            # Check for phase updates
            current_phase = session.get("current_phase")
            if current_phase != last_phase:
                await websocket.send_json({
                    "type": "phase_update",
                    "phase": current_phase
                })
                last_phase = current_phase

            # Check for agent updates
            agents_state = session.get("agents", {})
            if agents_state != last_agents_state:
                for agent_name, agent_info in agents_state.items():
                    # Check if this agent has changed (status, duration, or output)
                    last_agent = last_agents_state.get(agent_name, {})
                    agent_changed = (
                        agent_name not in last_agents_state or
                        last_agent.get("status") != agent_info.get("status") or
                        last_agent.get("duration") != agent_info.get("duration") or
                        last_agent.get("output") != agent_info.get("output")
                    )
                    
                    if agent_changed:
                        await websocket.send_json({
                            "type": "agent_update",
                            "agent": agent_name,
                            "status": agent_info.get("status", "pending"),
                            "duration": agent_info.get("duration", 0),
                            "output": agent_info.get("output", "") or ""  # Ensure output is always sent, even if empty
                        })
                last_agents_state = {k: dict(v) for k, v in agents_state.items()}  # Deep copy for proper comparison

        # Send final result
        if session["status"] == "success":
            final_output = session.get("output") or ""
            # If no output in session, try to get from Final Answer agent
            if not final_output and "Final Answer" in session.get("agents", {}):
                final_output = session["agents"]["Final Answer"].get("output", "")
            
            logger.info(f"Sending complete message for session {session_id}, output length: {len(final_output) if final_output else 0}")
            
            await websocket.send_json({
                "type": "complete",
                "status": "success",
                "execution_time_ms": session.get("execution_time_ms"),
                "output": final_output,
                "final_answer": final_output
            })
        else:
            error_msg = session.get("error", "Unknown error occurred")
            logger.warning(f"Sending error complete message for session {session_id}: {error_msg}")
            await websocket.send_json({
                "type": "complete",
                "status": "error",
                "error": error_msg,
                "output": f"Error: {error_msg}",  # Include error in output field too
                "final_answer": f"Error: {error_msg}"
            })

    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e)
            })
        except:
            pass
    finally:
        # Unregister connection
        try:
            if session_id in session_websockets:
                session_websockets[session_id].remove(websocket)
                if not session_websockets[session_id]:
                    del session_websockets[session_id]
        except:
            pass

        try:
            await websocket.close()
        except:
            pass


# ============================================================================
# Internal Helper Functions
# ============================================================================

async def _run_council_async(
    session_id: str,
    query: str,
    output_mode: str,
    api_keys: Dict[str, str],
    preferred_providers: Optional[Dict[str, ProviderType]] = None,
    context_pack: Optional[Dict[str, Any]] = None,
    lexicon_lock: Optional[Dict[str, List[str]]] = None,
    output_contract: Optional[Dict[str, Any]] = None,
    transparency_mode: bool = False
):
    """Run council orchestration asynchronously."""

    session = council_sessions[session_id]

    try:
        session["status"] = "running"
        import time
        agent_start_times = {}

        # Progress callback
        async def progress_callback(event: Dict[str, Any]):
            agent_name = event.get("agent")
            event_type = event.get("type")

            # Track phase updates
            if event_type == "phase_start":
                phase_message = event.get("message", event.get("phase"))
                session["current_phase"] = phase_message
                # Immediately broadcast phase update
                await broadcast_to_session(session_id, {
                    "type": "phase_update",
                    "phase": phase_message
                })

            # Track agent execution
            elif event_type == "agent_start":
                if agent_name:
                    agent_start_times[agent_name] = time.time()
                    if agent_name in session["agents"]:
                        session["agents"][agent_name]["status"] = "running"
                        session["agents"][agent_name]["duration"] = 0
                        # Immediately broadcast agent start update
                        await broadcast_to_session(session_id, {
                            "type": "agent_update",
                            "agent": agent_name,
                            "status": "running",
                            "duration": 0,
                            "output": ""
                        })

            elif event_type == "agent_complete":
                if agent_name and agent_name in session["agents"]:
                    # Check if this is an error status
                    agent_status = event.get("status", "complete")
                    session["agents"][agent_name]["status"] = agent_status
                    if agent_name in agent_start_times:
                        duration = time.time() - agent_start_times[agent_name]
                        session["agents"][agent_name]["duration"] = int(duration)
                    # Always store the output (which may contain error message)
                    output = event.get("output", "")
                    session["agents"][agent_name]["output"] = output
                    # If it's an error, also log it
                    if agent_status == "error":
                        logger.warning(f"Agent {agent_name} completed with error: {output}")
                    
                    # Immediately broadcast the agent update to all connected WebSockets
                    await broadcast_to_session(session_id, {
                        "type": "agent_update",
                        "agent": agent_name,
                        "status": agent_status,
                        "duration": session["agents"][agent_name]["duration"],
                        "output": output
                    })

            elif event_type == "agent_output":
                if agent_name and agent_name in session["agents"]:
                    session["agents"][agent_name]["output"] = event.get("output", "")
                    if agent_name in agent_start_times:
                        duration = time.time() - agent_start_times[agent_name]
                        session["agents"][agent_name]["duration"] = int(duration)

            # Track errors
            elif event_type == "error":
                session["status"] = "error"
                error_msg = event.get("error", "Unknown error occurred")
                session["error"] = error_msg
                if agent_name and agent_name in session["agents"]:
                    session["agents"][agent_name]["status"] = "error"
                    # Store error message in output so it's visible in UI
                    error_output = f"Error: {error_msg}"
                    session["agents"][agent_name]["output"] = error_output
                    # Immediately broadcast agent error update
                    await broadcast_to_session(session_id, {
                        "type": "agent_update",
                        "agent": agent_name,
                        "status": "error",
                        "duration": session["agents"][agent_name].get("duration", 0),
                        "output": error_output
                    })

            # Track completion
            elif event_type == "complete":
                session["status"] = "success"
                final_output = event.get("output", "")
                session["output"] = final_output
                # Mark Final Answer as complete
                if "Final Answer" in session["agents"]:
                    session["agents"]["Final Answer"]["status"] = "complete"
                    session["agents"]["Final Answer"]["output"] = final_output
                
                # Immediately broadcast completion
                await broadcast_to_session(session_id, {
                    "type": "complete",
                    "status": "success",
                    "execution_time_ms": session.get("execution_time_ms"),
                    "output": final_output,
                    "final_answer": final_output
                })

        # Create config
        config = CouncilConfig(
            query=query,
            output_mode=OutputMode(output_mode),
            api_keys=api_keys,
            preferred_providers=preferred_providers,
            verbose=True,
            context_pack=context_pack,
            lexicon_lock=lexicon_lock,
            output_contract=output_contract,
            transparency_mode=transparency_mode
        )

        # Run council
        orchestrator = CouncilOrchestrator()
        result = await orchestrator.run(config, progress_callback=progress_callback)

        # Store result
        session["status"] = result.status
        session["output"] = result.output
        session["error"] = result.error
        session["execution_time_ms"] = result.execution_time_ms

        logger.info(
            f"Council session {session_id} completed",
            extra={
                "status": result.status,
                "execution_time_ms": result.execution_time_ms
            }
        )

    except Exception as e:
        logger.error(f"Council session {session_id} failed: {e}", exc_info=True)
        session["status"] = "error"
        session["error"] = str(e)
