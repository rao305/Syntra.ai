# Multi-Agent Council - Implementation & Integration Guide

**Date:** 2025-12-12
**Version:** 1.0
**Status:** Active

---

## Quick Start

### 1. Install Dependencies
```bash
pip install openai asyncio
```

### 2. Set API Key
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### 3. Run Standalone Example
```bash
python council.py --query "Your task here" --mode deliverable-ownership
```

---

## System Architecture

```
┌─────────────────────────────────────────┐
│      Frontend (Syntra UI)                │
│   - Collaboration Panel                  │
│   - Query Input Form                     │
│   - Output Modes Dropdown                │
└──────────────┬──────────────────────────┘
               │ POST /api/collaboration/council
               ▼
┌─────────────────────────────────────────┐
│    FastAPI Backend Service               │
│   - /api/collaboration/council           │
│   - /api/collaboration/status/:id        │
│   - WebSocket /ws/collaboration/:id      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   Multi-Agent Council Orchestrator       │
│   - Phase 1: 5 Parallel Agents           │
│   - Phase 2: Debate Synthesizer          │
│   - Phase 3: Judge Agent                 │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│    OpenAI API (LLM Provider)             │
│   - gpt-4o model                         │
└─────────────────────────────────────────┘
```

---

## Backend Integration (FastAPI)

### 1. Create Collaboration Service File

**File:** `backend/app/services/collaboration_council.py`

```python
"""
Multi-Agent Council Orchestrator Service
Manages the collaboration workflow orchestration.
"""

import asyncio
import json
from typing import Literal
from openai import AsyncOpenAI
from datetime import datetime

client = AsyncOpenAI()  # Uses OPENAI_API_KEY environment variable

# =============================================================================
# SYSTEM PROMPTS (Agent Instructions)
# =============================================================================

ARCHITECT_PROMPT = """You are the **Architect Agent (Lead/PM)** - diplomatic, structured, safety-conscious.

**Your Ownership Areas:**
- Requirements capture & acceptance criteria
- System architecture & API design
- Repo layout & project structure
- Integration plan & sequencing

[See COLLABORATION_AGENTS.md for complete prompt]
"""

# [Include all 5 agent prompts from COLLABORATION_AGENTS.md]

# =============================================================================
# AGENT EXECUTION
# =============================================================================

async def run_agent(
    system_prompt: str,
    user_message: str,
    model: str = "gpt-4o",
    max_tokens: int = 1500
) -> str:
    """Execute a single agent with the given prompt."""
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=max_tokens,
        temperature=0.3  # Lower temperature for consistency
    )
    return response.choices[0].message.content


async def run_council(
    query: str,
    output_mode: Literal[
        "deliverable-only",
        "deliverable-ownership",
        "audit",
        "full-transcript"
    ] = "deliverable-ownership",
    progress_callback=None  # Optional: callback for progress updates
) -> dict:
    """
    Execute the full Multi-Agent Council workflow.

    Args:
        query: User's request
        output_mode: Output verbosity level
        progress_callback: Optional async callback for progress updates

    Returns:
        {
            "status": "success" | "error",
            "output": str,  # Final judge output
            "timestamp": datetime,
            "execution_time_ms": int,
            "tokens_used": {
                "phase1": int,
                "phase2": int,
                "phase3": int
            },
            "phase1_outputs": dict,  # Optional: individual agent outputs
            "error": str  # If status == "error"
        }
    """
    start_time = datetime.utcnow()

    try:
        # =====================================================================
        # PHASE 1: Run 5 agents in parallel
        # =====================================================================
        if progress_callback:
            await progress_callback("phase_1_start")

        phase1_tasks = [
            run_agent(ARCHITECT_PROMPT, query, max_tokens=1500),
            run_agent(DATA_ENGINEER_PROMPT, query, max_tokens=1500),
            run_agent(RESEARCHER_PROMPT, query, max_tokens=1500),
            run_agent(RED_TEAMER_PROMPT, query, max_tokens=1500),
            run_agent(OPTIMIZER_PROMPT, query, max_tokens=1500),
        ]

        phase1_results = await asyncio.gather(*phase1_tasks)

        if progress_callback:
            await progress_callback("phase_1_complete")

        architect_output = phase1_results[0]
        data_engineer_output = phase1_results[1]
        researcher_output = phase1_results[2]
        red_teamer_output = phase1_results[3]
        optimizer_output = phase1_results[4]

        # =====================================================================
        # PHASE 2: Run Debate Synthesizer
        # =====================================================================
        if progress_callback:
            await progress_callback("phase_2_start")

        synthesizer_input = f"""Original Query: {query}

---

🤖 ARCHITECT'S ANALYSIS:
{architect_output}

---

🌌 DATA ENGINEER'S ANALYSIS:
{data_engineer_output}

---

🦅 RESEARCHER'S ANALYSIS:
{researcher_output}

---

🚀 RED TEAMER'S ANALYSIS:
{red_teamer_output}

---

🌙 OPTIMIZER'S ANALYSIS:
{optimizer_output}"""

        synthesis = await run_agent(
            SYNTHESIZER_PROMPT,
            synthesizer_input,
            max_tokens=3000
        )

        if progress_callback:
            await progress_callback("phase_2_complete")

        # =====================================================================
        # PHASE 3: Run Judge Agent
        # =====================================================================
        if progress_callback:
            await progress_callback("phase_3_start")

        judge_input = f"""Original Query: {query}

Output Mode: {output_mode}

---

SYNTHESIZED DEBATE:
{synthesis}"""

        # Add full transcript if requested
        if output_mode == "full-transcript":
            judge_input += f"""

---
FULL COUNCIL TRANSCRIPT:

🤖 ARCHITECT:
{architect_output}

🌌 DATA ENGINEER:
{data_engineer_output}

🦅 RESEARCHER:
{researcher_output}

🚀 RED TEAMER:
{red_teamer_output}

🌙 OPTIMIZER:
{optimizer_output}"""

        judge_prompt = get_judge_prompt(output_mode)

        final_output = await run_agent(
            judge_prompt,
            judge_input,
            max_tokens=8000
        )

        if progress_callback:
            await progress_callback("phase_3_complete")

        # =====================================================================
        # Return Result
        # =====================================================================
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return {
            "status": "success",
            "output": final_output,
            "timestamp": start_time.isoformat(),
            "execution_time_ms": int(execution_time),
            "tokens_used": {
                "phase1": "estimate: ~5700",  # Can improve with token counting
                "phase2": "estimate: ~1500",
                "phase3": "estimate: ~2000"
            },
            "phase1_outputs": {
                "architect": architect_output,
                "data_engineer": data_engineer_output,
                "researcher": researcher_output,
                "red_teamer": red_teamer_output,
                "optimizer": optimizer_output
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": start_time.isoformat(),
            "execution_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
        }


def get_judge_prompt(output_mode: str) -> str:
    """Generate Judge prompt with conditional sections based on output mode."""
    # [See COLLABORATION_WORKFLOW.md for complete judge prompt]
    base_prompt = """You are **The Judge (Hard Gate QA)** - impartial, strict, quality-focused.
[... complete prompt ...]"""

    if output_mode in ["deliverable-ownership", "audit"]:
        base_prompt += "\n## Decision Log\n[...]\n"

    if output_mode == "audit":
        base_prompt += "\n## Risk Register\n[...]\n"

    if output_mode == "full-transcript":
        base_prompt += "\n---\n## Appendix: Council Transcript\n[...]\n"

    return base_prompt
```

### 2. Create FastAPI Endpoint

**File:** `backend/app/api/collaboration.py` (Updated/Create)

```python
"""
Collaboration API Endpoints
Handles Multi-Agent Council requests from frontend.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Literal, Optional
import uuid
from datetime import datetime

from app.services.collaboration_council import run_council

router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])

# In-memory store for demo; use Redis/DB in production
collaboration_tasks = {}


class CollaborationRequest(BaseModel):
    """Request to run Multi-Agent Council"""
    query: str
    output_mode: Literal[
        "deliverable-only",
        "deliverable-ownership",
        "audit",
        "full-transcript"
    ] = "deliverable-ownership"


class CollaborationResponse(BaseModel):
    """Response from council execution"""
    task_id: str
    status: str  # "pending", "running", "success", "error"
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


@router.post("/council")
async def run_collaboration_council(
    request: CollaborationRequest,
    background_tasks: BackgroundTasks
) -> CollaborationResponse:
    """
    Execute Multi-Agent Council for given query.

    Returns immediately with task_id for polling/WebSocket updates.
    """
    task_id = str(uuid.uuid4())

    # Store initial state
    collaboration_tasks[task_id] = {
        "status": "running",
        "created_at": datetime.utcnow(),
        "output": None,
        "error": None
    }

    # Progress callback
    async def progress_update(phase: str):
        if task_id in collaboration_tasks:
            collaboration_tasks[task_id]["current_phase"] = phase

    # Run council in background
    async def run_async():
        result = await run_council(
            query=request.query,
            output_mode=request.output_mode,
            progress_callback=progress_update
        )

        if task_id in collaboration_tasks:
            collaboration_tasks[task_id].update(result)

    background_tasks.add_task(run_async)

    return CollaborationResponse(
        task_id=task_id,
        status="running"
    )


@router.get("/council/{task_id}")
async def get_council_status(task_id: str) -> CollaborationResponse:
    """Check status of council execution."""
    if task_id not in collaboration_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = collaboration_tasks[task_id]
    return CollaborationResponse(
        task_id=task_id,
        status=task["status"],
        output=task.get("output"),
        error=task.get("error"),
        execution_time_ms=task.get("execution_time_ms")
    )


@router.delete("/council/{task_id}")
async def cancel_council(task_id: str) -> dict:
    """Cancel running council task."""
    if task_id not in collaboration_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = collaboration_tasks[task_id]
    if task["status"] == "running":
        task["status"] = "cancelled"
        return {"status": "cancelled"}
    else:
        raise HTTPException(status_code=400, detail="Task is not running")
```

### 3. Add WebSocket for Real-Time Updates

**File:** `backend/app/api/collaboration.py` (Add to existing)

```python
from fastapi import WebSocket
import json

@router.websocket("/ws/collaboration/{task_id}")
async def websocket_council_updates(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time progress updates."""
    await websocket.accept()

    try:
        if task_id not in collaboration_tasks:
            await websocket.send_json({
                "type": "error",
                "message": "Task not found"
            })
            await websocket.close(code=4004)
            return

        # Send initial status
        task = collaboration_tasks[task_id]
        await websocket.send_json({
            "type": "status",
            "task_id": task_id,
            "status": task["status"],
            "created_at": task["created_at"].isoformat()
        })

        # Poll for updates
        while task["status"] in ["pending", "running"]:
            await asyncio.sleep(1)  # Check every 1 second

            await websocket.send_json({
                "type": "progress",
                "current_phase": task.get("current_phase", "unknown")
            })

        # Send final result
        if task["status"] == "success":
            await websocket.send_json({
                "type": "complete",
                "status": "success",
                "execution_time_ms": task.get("execution_time_ms"),
                "output": task.get("output")
            })
        else:
            await websocket.send_json({
                "type": "complete",
                "status": "error",
                "error": task.get("error")
            })

    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()
```

---

## Frontend Integration (React/TypeScript)

### 1. Create Collaboration Hook

**File:** `frontend/lib/hooks/useCollaborationCouncil.ts`

```typescript
import { useState, useCallback, useRef, useEffect } from 'react'

type OutputMode = 'deliverable-only' | 'deliverable-ownership' | 'audit' | 'full-transcript'
type Phase = 'phase_1_start' | 'phase_1_complete' | 'phase_2_start' | 'phase_2_complete' | 'phase_3_start' | 'phase_3_complete'

interface UseCollaborationCouncilState {
  status: 'idle' | 'running' | 'success' | 'error' | 'cancelled'
  currentPhase: Phase | null
  output: string | null
  error: string | null
  executionTimeMs: number | null
  taskId: string | null
}

export function useCollaborationCouncil() {
  const [state, setState] = useState<UseCollaborationCouncilState>({
    status: 'idle',
    currentPhase: null,
    output: null,
    error: null,
    executionTimeMs: null,
    taskId: null
  })

  const wsRef = useRef<WebSocket | null>(null)

  // Start council execution
  const startCouncil = useCallback(
    async (query: string, outputMode: OutputMode = 'deliverable-ownership') => {
      try {
        setState(prev => ({
          ...prev,
          status: 'running',
          output: null,
          error: null,
          currentPhase: null
        }))

        // POST to start council
        const response = await fetch('/api/collaboration/council', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            output_mode: outputMode
          })
        })

        if (!response.ok) {
          throw new Error(`Failed to start council: ${response.statusText}`)
        }

        const { task_id } = await response.json()
        setState(prev => ({ ...prev, taskId: task_id }))

        // Connect WebSocket for updates
        connectWebSocket(task_id)
      } catch (err) {
        setState(prev => ({
          ...prev,
          status: 'error',
          error: err instanceof Error ? err.message : 'Unknown error'
        }))
      }
    },
    []
  )

  // Connect to WebSocket for real-time updates
  const connectWebSocket = useCallback((taskId: string) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/collaboration/ws/${taskId}`

    wsRef.current = new WebSocket(wsUrl)

    wsRef.current.onmessage = (event) => {
      const message = JSON.parse(event.data)

      if (message.type === 'progress') {
        setState(prev => ({
          ...prev,
          currentPhase: message.current_phase
        }))
      } else if (message.type === 'complete') {
        setState(prev => ({
          ...prev,
          status: message.status,
          output: message.output,
          error: message.error,
          executionTimeMs: message.execution_time_ms
        }))
      } else if (message.type === 'error') {
        setState(prev => ({
          ...prev,
          status: 'error',
          error: message.message
        }))
      }
    }

    wsRef.current.onerror = () => {
      setState(prev => ({
        ...prev,
        status: 'error',
        error: 'WebSocket connection error'
      }))
    }
  }, [])

  // Cancel running council
  const cancelCouncil = useCallback(async () => {
    if (!state.taskId) return

    try {
      await fetch(`/api/collaboration/council/${state.taskId}`, {
        method: 'DELETE'
      })
      setState(prev => ({ ...prev, status: 'cancelled' }))
      if (wsRef.current) {
        wsRef.current.close()
      }
    } catch (err) {
      console.error('Failed to cancel council:', err)
    }
  }, [state.taskId])

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  return {
    ...state,
    startCouncil,
    cancelCouncil
  }
}
```

### 2. Create Collaboration UI Component

**File:** `frontend/app/collaboration/council-panel.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useCollaborationCouncil } from '@/lib/hooks/useCollaborationCouncil'

export function CouncilPanel() {
  const [query, setQuery] = useState('')
  const [outputMode, setOutputMode] = useState<'deliverable-only' | 'deliverable-ownership' | 'audit' | 'full-transcript'>(
    'deliverable-ownership'
  )

  const council = useCollaborationCouncil()

  const handleStart = () => {
    if (query.trim()) {
      council.startCouncil(query, outputMode)
    }
  }

  const phaseLabels = {
    phase_1_start: 'Starting 5 specialist agents...',
    phase_1_complete: 'Phase 1 complete - running synthesizer...',
    phase_2_start: 'Synthesizing debate...',
    phase_2_complete: 'Synthesis complete - running judge...',
    phase_3_start: 'Running judge validation...',
    phase_3_complete: 'Judge complete - finalizing output...'
  }

  return (
    <div className="space-y-4 p-4 border rounded-lg">
      <h2 className="text-2xl font-bold">Multi-Agent Council</h2>

      {council.status === 'idle' ? (
        <div className="space-y-4">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe what you want the council to build or decide on..."
            className="w-full h-32 p-2 border rounded"
          />

          <div className="space-y-2">
            <label className="block font-semibold">Output Mode:</label>
            <select
              value={outputMode}
              onChange={(e) => setOutputMode(e.target.value as any)}
              className="p-2 border rounded"
            >
              <option value="deliverable-only">Code Only</option>
              <option value="deliverable-ownership">Code + Ownership (Recommended)</option>
              <option value="audit">Code + Audit Trail</option>
              <option value="full-transcript">Full Transcript</option>
            </select>
          </div>

          <button
            onClick={handleStart}
            disabled={!query.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
          >
            Start Council
          </button>
        </div>
      ) : council.status === 'running' ? (
        <div className="space-y-4">
          <div className="animate-pulse text-gray-600">
            {council.currentPhase && phaseLabels[council.currentPhase as keyof typeof phaseLabels]}
          </div>

          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{
                width: council.currentPhase?.includes('phase_1')
                  ? '33%'
                  : council.currentPhase?.includes('phase_2')
                    ? '66%'
                    : '99%'
              }}
            />
          </div>

          <button
            onClick={council.cancelCouncil}
            className="px-4 py-2 bg-red-600 text-white rounded"
          >
            Cancel
          </button>
        </div>
      ) : council.status === 'success' ? (
        <div className="space-y-4">
          <div className="text-green-600 font-bold">Council Complete ✓</div>
          {council.executionTimeMs && (
            <div className="text-sm text-gray-600">
              Execution time: {council.executionTimeMs}ms
            </div>
          )}
          <div className="bg-gray-100 p-4 rounded max-h-96 overflow-y-auto">
            <pre className="whitespace-pre-wrap text-sm">{council.output}</pre>
          </div>
          <button
            onClick={() => council.setState({ status: 'idle', output: null })}
            className="px-4 py-2 bg-blue-600 text-white rounded"
          >
            New Council
          </button>
        </div>
      ) : (
        <div className="text-red-600">
          Error: {council.error}
          <button
            onClick={() => council.setState({ status: 'idle', output: null, error: null })}
            className="ml-4 px-4 py-2 bg-blue-600 text-white rounded"
          >
            Reset
          </button>
        </div>
      )}
    </div>
  )
}
```

---

## Deployment Checklist

- [ ] Set `OPENAI_API_KEY` environment variable in production
- [ ] Configure Redis/database for task persistence (replace in-memory store)
- [ ] Add rate limiting on `/api/collaboration/council` endpoint
- [ ] Configure CORS if frontend is on different domain
- [ ] Add logging/monitoring for council execution
- [ ] Set up error alerting for failed executions
- [ ] Configure max tokens/timeout limits for safety
- [ ] Add authentication/authorization checks
- [ ] Test WebSocket connection in production environment
- [ ] Load test the endpoint (expect ~30s per execution, plan for concurrent requests)

---

## Configuration

Create `backend/.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
COLLABORATION_MAX_TOKENS=8000
COLLABORATION_TIMEOUT_SECONDS=120
```

---

## Monitoring & Debugging

### Check Recent Executions
```bash
curl http://localhost:8000/api/collaboration/council/task-id
```

### Stream Council Output via WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/api/collaboration/ws/task-id')
ws.onmessage = (event) => {
  const message = JSON.parse(event.data)
  console.log('Phase:', message.current_phase)
}
```

### Example Council Request
```bash
curl -X POST http://localhost:8000/api/collaboration/council \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create a simple FastAPI service with SQLite that exposes POST /events and GET /health",
    "output_mode": "deliverable-ownership"
  }'
```

---

## Troubleshooting

### "API Key not found"
- Ensure `OPENAI_API_KEY` is set in environment variables
- Check: `echo $OPENAI_API_KEY`

### "Task not found" when checking status
- Task was garbage collected (lives only for session)
- Switch to Redis backend for persistence: see deployment section

### WebSocket connection fails in production
- Check HTTPS/WSS upgrade: protocol should be `wss://` not `ws://`
- Verify CORS and WebSocket proxy settings
- Check firewall/load balancer WebSocket support

### Council takes very long (>120s)
- Check OpenAI API rate limits
- Reduce `max_tokens` in phase 1 agents
- Check network latency between backend and OpenAI

---

## Next Steps

1. Copy all agent prompts from `COLLABORATION_AGENTS.md` into `collaboration_council.py`
2. Update backend `.env` with OpenAI API key
3. Integrate `CouncilPanel` component into your collaboration UI
4. Test with sample query in development
5. Deploy to production following deployment checklist

See:
- `COLLABORATION_ARCHITECTURE.md` - System design
- `COLLABORATION_AGENTS.md` - Agent prompts and rules
- `COLLABORATION_WORKFLOW.md` - Execution flow details
