"""
Dynamic Collaboration API Endpoints

API routes for the dynamic role-based collaboration system that
assigns models to roles based on query requirements and model capabilities.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json
import asyncio

from app.database import get_db
from app.security import set_rls_context
from app.api.deps import require_org_id
from app.services.provider_keys import get_api_key_for_org
from app.models.provider_key import ProviderType
from app.services.dynamic_orchestrator import (
    dynamic_orchestrator,
    UserPriority,
    CollaborationPlan,
    CollaborationResult,
    CollabStep
)
from app.services.model_capabilities import (
    get_available_models,
    format_models_for_orchestrator,
    MODEL_CAPABILITIES
)

import logging
logger = logging.getLogger(__name__)


router = APIRouter()


# Request/Response Models

class UserSettings(BaseModel):
    """User preferences for collaboration"""
    priority: str = Field(
        default="balanced",
        description="Priority mode: quality | balanced | speed | cost"
    )
    max_steps: int = Field(
        default=5,
        ge=1,
        le=7,
        description="Maximum number of collaboration steps"
    )


class DynamicCollaborateRequest(BaseModel):
    """Request for dynamic collaboration"""
    user_id: Optional[str] = None
    message: str = Field(..., description="User's message or question")
    thread_id: Optional[str] = Field(None, description="Thread ID for context")
    thread_context: Optional[str] = Field(None, description="Previous conversation context")
    settings: Optional[UserSettings] = Field(default_factory=UserSettings)


class StepResultResponse(BaseModel):
    """Response for a single collaboration step"""
    step_index: int
    role: str
    model_id: str
    model_name: str
    purpose: str
    content: str
    execution_time_ms: float
    success: bool
    error: Optional[str] = None


class CollaborationPlanResponse(BaseModel):
    """Response for collaboration plan"""
    pipeline_summary: str
    steps: List[Dict[str, Any]]
    planning_time_ms: float


class DynamicCollaborateResponse(BaseModel):
    """Response from dynamic collaboration"""
    turn_id: str
    final_answer: str
    plan: CollaborationPlanResponse
    step_results: List[StepResultResponse]
    total_time_ms: float
    available_models_used: List[str]


class AvailableModelsResponse(BaseModel):
    """Response listing available models"""
    models: List[Dict[str, Any]]
    total_count: int


# Helper functions

async def get_org_api_keys(db: AsyncSession, org_id: str) -> Dict[str, str]:
    """Collect API keys for all providers for an organization"""
    api_keys = {}
    providers = [
        ProviderType.OPENAI,
        ProviderType.GEMINI,
        ProviderType.PERPLEXITY,
        ProviderType.KIMI
    ]
    
    for provider in providers:
        try:
            key = await get_api_key_for_org(db, org_id, provider)
            if key:
                api_keys[provider.value] = key
        except Exception as e:
            logger.info("Could not get API key for {provider.value}: {e}")
            continue
    
    return api_keys


def format_step_result(step_result, plan: CollaborationPlan) -> StepResultResponse:
    """Format a step result for API response"""
    # Find the step in the plan to get additional info
    plan_step = next(
        (s for s in plan.steps if s.step_index == step_result.step_index),
        None
    )
    
    # Get model display name
    model_info = MODEL_CAPABILITIES.get(step_result.model_id)
    model_name = model_info.display_name if model_info else step_result.model_id
    
    return StepResultResponse(
        step_index=step_result.step_index,
        role=step_result.role,
        model_id=step_result.model_id,
        model_name=model_name,
        purpose=plan_step.purpose if plan_step else "",
        content=step_result.content,
        execution_time_ms=step_result.execution_time_ms,
        success=step_result.success,
        error=step_result.error
    )


# API Endpoints

@router.get("/available-models")
async def list_available_models(
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
) -> AvailableModelsResponse:
    """
    List all available models for collaboration based on configured API keys.
    
    Returns model capabilities including strengths, cost tier, and features.
    """
    await set_rls_context(db, org_id)
    
    # Get API keys for organization
    api_keys = await get_org_api_keys(db, org_id)
    
    if not api_keys:
        return AvailableModelsResponse(models=[], total_count=0)
    
    # Get available models
    available = get_available_models(api_keys)
    formatted = format_models_for_orchestrator(available)
    
    return AvailableModelsResponse(
        models=formatted,
        total_count=len(formatted)
    )


@router.post("/plan")
async def create_collaboration_plan(
    request: DynamicCollaborateRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
) -> CollaborationPlanResponse:
    """
    Create a collaboration plan without executing it.
    
    Useful for previewing what the orchestrator will do.
    """
    await set_rls_context(db, org_id)
    
    # Get API keys
    api_keys = await get_org_api_keys(db, org_id)
    
    if not api_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No API keys configured for collaboration"
        )
    
    # Parse priority
    try:
        priority = UserPriority(request.settings.priority)
    except ValueError:
        priority = UserPriority.BALANCED
    
    # Create plan
    plan = await dynamic_orchestrator.create_plan(
        user_message=request.message,
        api_keys=api_keys,
        thread_context=request.thread_context,
        priority=priority,
        max_steps=request.settings.max_steps
    )
    
    # Format steps for response
    steps_data = []
    for step in plan.steps:
        model_info = MODEL_CAPABILITIES.get(step.model_id)
        steps_data.append({
            "step_index": step.step_index,
            "role": step.role.value,
            "model_id": step.model_id,
            "model_name": model_info.display_name if model_info else step.model_id,
            "purpose": step.purpose,
            "needs_previous_steps": step.needs_previous_steps,
            "estimated_importance": step.estimated_importance,
            "model_rationale": step.model_rationale
        })
    
    return CollaborationPlanResponse(
        pipeline_summary=plan.pipeline_summary,
        steps=steps_data,
        planning_time_ms=plan.planning_time_ms
    )


@router.post("/run")
async def run_dynamic_collaboration(
    request: DynamicCollaborateRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
) -> DynamicCollaborateResponse:
    """
    Run a complete dynamic collaboration.
    
    This endpoint:
    1. Creates a collaboration plan using the orchestrator LLM
    2. Executes each step in sequence
    3. Returns the final synthesized answer with all step outputs
    
    The orchestrator dynamically selects the best model for each role
    based on the query requirements and model capabilities.
    """
    await set_rls_context(db, org_id)
    
    # Get API keys
    api_keys = await get_org_api_keys(db, org_id)
    
    if not api_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No API keys configured for collaboration. Please add at least one provider API key."
        )
    
    # Generate turn ID
    turn_id = str(uuid.uuid4())
    
    # Parse priority
    try:
        priority = UserPriority(request.settings.priority)
    except ValueError:
        priority = UserPriority.BALANCED
    
    # Run collaboration
    try:
        result = await dynamic_orchestrator.run_collaboration(
            user_message=request.message,
            api_keys=api_keys,
            turn_id=turn_id,
            thread_context=request.thread_context,
            priority=priority,
            max_steps=request.settings.max_steps
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Collaboration failed: {str(e)}"
        )
    
    # Format response
    step_responses = [
        format_step_result(sr, result.plan) 
        for sr in result.step_results
    ]
    
    # Get list of models used
    models_used = list(set(sr.model_id for sr in result.step_results))
    
    # Format plan
    plan_steps = []
    for step in result.plan.steps:
        model_info = MODEL_CAPABILITIES.get(step.model_id)
        plan_steps.append({
            "step_index": step.step_index,
            "role": step.role.value,
            "model_id": step.model_id,
            "model_name": model_info.display_name if model_info else step.model_id,
            "purpose": step.purpose,
            "needs_previous_steps": step.needs_previous_steps,
            "estimated_importance": step.estimated_importance,
            "model_rationale": step.model_rationale
        })
    
    return DynamicCollaborateResponse(
        turn_id=turn_id,
        final_answer=result.final_answer,
        plan=CollaborationPlanResponse(
            pipeline_summary=result.plan.pipeline_summary,
            steps=plan_steps,
            planning_time_ms=result.plan.planning_time_ms
        ),
        step_results=step_responses,
        total_time_ms=result.total_time_ms,
        available_models_used=models_used
    )


@router.post("/run/stream")
async def run_dynamic_collaboration_stream(
    request: DynamicCollaborateRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Run dynamic collaboration with streaming updates.
    
    Sends Server-Sent Events (SSE) for:
    - plan_created: When the collaboration plan is ready
    - step_started: When each step begins
    - step_completed: When each step finishes
    - final_answer: The complete synthesized response
    """
    await set_rls_context(db, org_id)
    
    # Get API keys
    api_keys = await get_org_api_keys(db, org_id)
    
    if not api_keys:
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': 'No API keys configured'})}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream"
        )
    
    turn_id = str(uuid.uuid4())
    
    try:
        priority = UserPriority(request.settings.priority)
    except ValueError:
        priority = UserPriority.BALANCED
    
    async def generate_stream():
        try:
            # Create plan
            yield f"data: {json.dumps({'type': 'planning', 'message': 'Creating collaboration plan...'})}\n\n"
            
            plan = await dynamic_orchestrator.create_plan(
                user_message=request.message,
                api_keys=api_keys,
                thread_context=request.thread_context,
                priority=priority,
                max_steps=request.settings.max_steps
            )
            
            # Send plan
            plan_data = {
                "type": "plan_created",
                "plan": {
                    "pipeline_summary": plan.pipeline_summary,
                    "steps": [
                        {
                            "step_index": s.step_index,
                            "role": s.role.value,
                            "model_id": s.model_id,
                            "purpose": s.purpose
                        }
                        for s in plan.steps
                    ],
                    "planning_time_ms": plan.planning_time_ms
                }
            }
            yield f"data: {json.dumps(plan_data)}\n\n"
            
            # Execute each step
            step_outputs: Dict[str, str] = {}
            step_results = []
            
            for step in plan.steps:
                # Notify step start
                yield f"data: {json.dumps({'type': 'step_started', 'step_index': step.step_index, 'role': step.role.value, 'model_id': step.model_id})}\n\n"
                
                try:
                    # Build context
                    context_parts = [f"User Query: {request.message}"]
                    if request.thread_context:
                        context_parts.append(f"\nThread Context:\n{request.thread_context}")
                    for prev_role in step.needs_previous_steps:
                        if prev_role in step_outputs:
                            context_parts.append(f"\n{prev_role.upper()} Output:\n{step_outputs[prev_role]}")
                    
                    full_context = "\n".join(context_parts)
                    
                    # Get model info
                    from app.services.model_capabilities import get_model_by_id
                    model_info = get_model_by_id(step.model_id)
                    
                    if not model_info:
                        raise ValueError(f"Model {step.model_id} not found")
                    
                    api_key = api_keys.get(model_info.provider.value)
                    if not api_key:
                        raise ValueError(f"No API key for {model_info.provider.value}")
                    
                    # Call model
                    import time
                    start = time.perf_counter()
                    
                    content = await dynamic_orchestrator._call_model(
                        provider=model_info.provider,
                        model=model_info.model_name,
                        messages=[
                            {"role": "system", "content": step.instructions_for_step},
                            {"role": "user", "content": full_context}
                        ],
                        api_key=api_key
                    )
                    
                    exec_time = (time.perf_counter() - start) * 1000
                    
                    step_outputs[step.role.value] = content
                    step_results.append({
                        "step_index": step.step_index,
                        "role": step.role.value,
                        "content": content,
                        "success": True
                    })
                    
                    # Send step completion
                    yield f"data: {json.dumps({'type': 'step_completed', 'step_index': step.step_index, 'role': step.role.value, 'content': content[:500] + '...' if len(content) > 500 else content, 'execution_time_ms': exec_time, 'success': True})}\n\n"
                    
                except Exception as e:
                    step_results.append({
                        "step_index": step.step_index,
                        "role": step.role.value,
                        "error": str(e),
                        "success": False
                    })
                    yield f"data: {json.dumps({'type': 'step_completed', 'step_index': step.step_index, 'role': step.role.value, 'success': False, 'error': str(e)})}\n\n"
            
            # Get final answer
            final_answer = ""
            for sr in reversed(step_results):
                if sr.get("success") and sr.get("content"):
                    final_answer = sr["content"]
                    break
            
            if not final_answer:
                final_answer = "I apologize, but I was unable to generate a response."
            
            # Send final answer
            yield f"data: {json.dumps({'type': 'final_answer', 'turn_id': turn_id, 'content': final_answer})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/capabilities")
async def get_model_capabilities():
    """
    Get the complete model capabilities registry.
    
    Returns all known models with their capability scores,
    regardless of API key availability.
    """
    capabilities = []
    for model_id, cap in MODEL_CAPABILITIES.items():
        capabilities.append(cap.to_dict())
    
    return {
        "models": capabilities,
        "total_count": len(capabilities)
    }





