# Multi-Agent Council Integration Guide

**Date:** 2025-12-12
**Version:** 1.0
**Status:** Ready for Integration

---

## Overview

The Multi-Agent Council Orchestrator has been fully integrated into the Syntra backend with support for all four AI providers:
- ✅ **OpenAI** (GPT-4o) - Default for architects, judges, synthesizers
- ✅ **Gemini** - Secondary for red teamers, threat modeling
- ✅ **Perplexity** - Research and web search capability
- ✅ **Kimi** (Claude) - Alternative reasoning model

---

## Backend Implementation

### File Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── council.py                    # NEW: Council API endpoints
│   │   └── collaboration.py              # Existing collaboration endpoints
│   └── services/
│       └── council/                      # NEW: Council orchestrator
│           ├── __init__.py
│           ├── config.py                 # Provider mappings & configuration
│           ├── base.py                   # Base agent executor with provider support
│           ├── orchestrator.py           # Main orchestration logic (3-phase workflow)
│           └── agents/
│               ├── __init__.py
│               ├── architect.py          # 🤖 Architect agent
│               ├── data_engineer.py      # 🌌 Data Engineer agent
│               ├── researcher.py         # 🦅 Researcher agent
│               ├── red_teamer.py         # 🚀 Red Teamer agent
│               ├── optimizer.py          # 🌙 Optimizer agent
│               ├── synthesizer.py        # 📋 Synthesizer
│               └── judge.py              # ⚖️ Judge agent
├── main.py                               # Updated to register council router
└── config.py                             # Existing configuration
```

### Key Integration Points

#### 1. Provider Dispatch (`app/services/council/base.py`)

The council system uses the existing provider dispatcher to support all configured providers:

```python
async def run_agent(
    agent_name: str,
    system_prompt: str,
    user_message: str,
    api_keys: Dict[str, str],
    preferred_provider: Optional[ProviderType] = None,
    max_tokens: Optional[int] = None
) -> tuple[str, ProviderType]:
    """
    Execute a single agent with any configured provider.

    - Automatically selects fastest models per provider
    - Handles token limits and completion budgets
    - Returns response + provider used for tracking
    """
```

#### 2. Provider Configuration (`app/services/council/config.py`)

```python
PROVIDER_MODELS = {
    ProviderType.OPENAI: "gpt-4o",           # Fastest GPT model
    ProviderType.GEMINI: "gemini-2.0-flash",# Fastest Gemini model
    ProviderType.PERPLEXITY: "sonar-pro",   # Research-optimized
    ProviderType.KIMI: "moonshot-v1-128k",  # Kimi's primary model
}

AGENT_PROVIDER_MAPPING = {
    "architect": ProviderType.OPENAI,
    "data_engineer": ProviderType.OPENAI,
    "researcher": ProviderType.PERPLEXITY,  # Web search capability
    "red_teamer": ProviderType.GEMINI,
    "optimizer": ProviderType.OPENAI,
    "synthesizer": ProviderType.OPENAI,
    "judge": ProviderType.OPENAI,
}
```

#### 3. API Endpoints (`app/api/council.py`)

Three new FastAPI endpoints:

```python
# Start council orchestration (async, returns session_id)
POST /api/council/orchestrate
{
    "query": "Create a FastAPI service with SQLite...",
    "output_mode": "deliverable-ownership",
    "preferred_providers": {
        "architect": "openai",
        "researcher": "perplexity",
        "judge": "gemini"
    }
}

# Check session status
GET /api/council/orchestrate/{session_id}

# Cancel running session
DELETE /api/council/orchestrate/{session_id}

# WebSocket for real-time progress
WS /api/council/ws/{session_id}
```

#### 4. Provider Key Integration

The council automatically retrieves API keys for all configured providers from the database:

```python
# In council endpoint
for provider in [ProviderType.OPENAI, ProviderType.GEMINI, ProviderType.PERPLEXITY, ProviderType.KIMI]:
    try:
        key = await get_api_key_for_org(db, org_id, provider)
        if key:
            api_keys[provider.value] = key  # Provider names: "openai", "gemini", etc.
    except Exception:
        continue
```

---

## API Usage

### 1. Start a Council Session

**Request:**
```bash
curl -X POST http://localhost:8000/api/council/orchestrate \
  -H "x-org-id: org_demo" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create a production-ready FastAPI microservice with SQLite idempotency",
    "output_mode": "deliverable-ownership"
  }'
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "current_phase": "Initializing..."
}
```

### 2. Check Status

**Request:**
```bash
curl http://localhost:8000/api/council/orchestrate/550e8400-e29b-41d4-a716-446655440000 \
  -H "x-org-id: org_demo"
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "current_phase": "Running Debate Synthesizer",
  "execution_time_ms": null,
  "output": null
}
```

### 3. Monitor with WebSocket

**JavaScript:**
```javascript
const sessionId = "550e8400-e29b-41d4-a716-446655440000";
const ws = new WebSocket(`ws://localhost:8000/api/council/ws/${sessionId}`);

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === "progress") {
    console.log("Current phase:", message.current_phase);
  } else if (message.type === "complete") {
    console.log("Final output:", message.output);
    console.log("Execution time:", message.execution_time_ms, "ms");
  }
};
```

### 4. Custom Provider Selection

You can specify preferred providers for specific agents:

**Request:**
```bash
curl -X POST http://localhost:8000/api/council/orchestrate \
  -H "x-org-id: org_demo" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "...",
    "output_mode": "audit",
    "preferred_providers": {
      "architect": "openai",
      "researcher": "perplexity",
      "red_teamer": "gemini",
      "judge": "kimi"
    }
  }'
```

---

## Multi-Provider Support Details

### Provider Selection Strategy

Each agent has a **preferred provider**, but falls back automatically if that provider's API key isn't configured:

| Agent | Preferred | Reason | Fallback |
|-------|-----------|--------|----------|
| Architect | OpenAI | Structured planning, GPT-4o | Any available |
| Data Engineer | OpenAI | Technical accuracy, code generation | Any available |
| Researcher | Perplexity | Web search capability | OpenAI |
| Red Teamer | Gemini | Creative threat modeling | OpenAI |
| Optimizer | OpenAI | Code optimization | Any available |
| Synthesizer | OpenAI | Complex synthesis | Any available |
| Judge | OpenAI | Final decisions | Any available |

### Token Budgets per Provider

```python
DEFAULT_COMPLETION_TOKENS = {
    ProviderType.OPENAI: 8192,      # Increase as needed
    ProviderType.GEMINI: 16384,     # Supports larger outputs
    ProviderType.PERPLEXITY: 8192,
    ProviderType.KIMI: 8192,
}
```

Can be overridden via environment variables:
```bash
OPENAI_MAX_OUTPUT_TOKENS=10000
GEMINI_MAX_OUTPUT_TOKENS=20000
PERPLEXITY_MAX_OUTPUT_TOKENS=10000
KIMI_MAX_OUTPUT_TOKENS=10000
```

---

## Output Modes

The council supports four output verbosity levels:

| Mode | Contents | Use Case |
|------|----------|----------|
| **deliverable-only** | Final code/solution | CI/CD pipelines |
| **deliverable-ownership** | Code + ownership map + checklist | Team collaboration (default) |
| **audit** | Above + risk register + decision log | Compliance, audits |
| **full-transcript** | Above + complete agent debate | Post-mortems, learning |

---

## Configuration

### Environment Variables

```bash
# Provider API Keys (handled by existing provider_keys system)
# No additional env vars needed - uses org-specific keys from database

# Token limits (optional overrides)
OPENAI_MAX_OUTPUT_TOKENS=8192
GEMINI_MAX_OUTPUT_TOKENS=16384
PERPLEXITY_MAX_OUTPUT_TOKENS=8192
KIMI_MAX_OUTPUT_TOKENS=8192
```

### Database Integration

The council automatically:
1. Retrieves API keys for all providers from `provider_keys` table
2. Filters by `org_id` for multi-tenant support
3. Respects encrypted key storage (existing security)
4. Handles missing keys gracefully with fallbacks

---

## Workflow Execution

### Three-Phase Execution

```
Phase 1 (5-15s, parallel):
├── 🤖 Architect → Requirements, architecture, file plan
├── 🌌 Data Engineer → Schema, idempotency, indexing
├── 🦅 Researcher → Dependencies, best practices
├── 🚀 Red Teamer → Threats, privacy, security
└── 🌙 Optimizer → Simplification, performance

        ↓

Phase 2 (3-5s, sequential):
└── 📋 Synthesizer → Merge all outputs, resolve conflicts, create ownership map

        ↓

Phase 3 (5-10s, sequential):
└── ⚖️ Judge → Validate, produce final deliverable with verdict
```

**Total Execution Time:** 13-30 seconds (varies by provider latency)

---

## Logging & Monitoring

### Log Output

All council executions are logged with structured information:

```
[INFO] 🚀 Starting Multi-Agent Council
[INFO] ⚡ Phase 1: Running 5 specialist agents in parallel...
[INFO] ✅ Phase 1 completed: duration_ms=8500
[INFO] 🔄 Phase 2: Running Debate Synthesizer...
[INFO] ✅ Phase 2 completed: duration_ms=4200
[INFO] ⚖️ Phase 3: Running Judge Agent...
[INFO] ✅ Phase 3 completed: duration_ms=6800
[INFO] ✅ Council complete: total_time_ms=19500
```

### WebSocket Events

The WebSocket endpoint emits these event types:

```json
{"type": "status", "session_id": "...", "status": "pending"}
{"type": "progress", "current_phase": "Running 5 specialist agents in parallel..."}
{"type": "complete", "status": "success", "execution_time_ms": 19500, "output": "..."}
{"type": "error", "error": "No API keys configured"}
```

---

## Error Handling

### Missing API Keys

If no API keys are configured for any provider:

```
Status: 400 Bad Request
{
  "detail": "No API keys configured. At least one provider required: openai, gemini, perplexity, or kimi"
}
```

### Provider Failure

If a specific provider fails, the council attempts fallback:

```python
# If OpenAI fails, try Gemini
# If Gemini fails, try Perplexity
# If all fail, return error with details
```

### Session Not Found

```
Status: 404 Not Found
{
  "detail": "Council session not found"
}
```

---

## Testing

### 1. Test with OpenAI Only

```bash
# Set only OpenAI key in database
curl -X POST http://localhost:8000/api/council/orchestrate \
  -H "x-org-id: org_demo" \
  -H "Content-Type: application/json" \
  -d '{"query": "Create a REST API", "output_mode": "deliverable-ownership"}'
```

### 2. Test with Multiple Providers

```bash
# Set OpenAI + Perplexity + Gemini keys in database
# All agents will use preferred providers with fallbacks available

curl -X POST http://localhost:8000/api/council/orchestrate \
  -H "x-org-id: org_demo" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Design a microservice architecture for SaaS",
    "output_mode": "audit",
    "preferred_providers": {
      "researcher": "perplexity"
    }
  }'
```

### 3. Test WebSocket Connection

```javascript
// HTML/JavaScript
const sessionId = "...";
const ws = new WebSocket(`ws://localhost:8000/api/council/ws/${sessionId}`);

ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.onerror = (e) => console.error("WebSocket error:", e);
ws.onclose = () => console.log("WebSocket closed");
```

---

## Frontend Integration

### React Hook Example

```typescript
import { useState } from 'react'

export function useCouncilOrchestrator() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [status, setStatus] = useState('idle')
  const [output, setOutput] = useState<string | null>(null)

  const startCouncil = async (query: string, outputMode = 'deliverable-ownership') => {
    const response = await fetch('/api/council/orchestrate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-org-id': orgId },
      body: JSON.stringify({ query, output_mode: outputMode })
    })

    const { session_id } = await response.json()
    setSessionId(session_id)
    setStatus('running')

    // Connect WebSocket for updates
    connectWebSocket(session_id)
  }

  const connectWebSocket = (id: string) => {
    const ws = new WebSocket(`ws://localhost:8000/api/council/ws/${id}`)

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      if (message.type === 'complete') {
        setStatus('success')
        setOutput(message.output)
      }
    }
  }

  return { sessionId, status, output, startCouncil }
}
```

---

## Deployment Checklist

- [ ] All provider API keys configured in `provider_keys` table
- [ ] Redis or persistent storage configured for session management (currently in-memory)
- [ ] Rate limiting on `/api/council/orchestrate` endpoint (recommended: 1 req/minute per org)
- [ ] CORS configured for frontend domain
- [ ] WebSocket CORS/proxy configured for production
- [ ] Logging aggregation set up (CloudWatch, ELK, etc.)
- [ ] Error alerting configured for council failures
- [ ] Load testing completed (expect ~30s per execution)
- [ ] Token budget limits verified for each provider
- [ ] Database backup strategy for session history (if persisting)

---

## Production Considerations

### Session Persistence

Current implementation uses in-memory storage. For production:

```python
# Option 1: Use Redis
import redis
redis_client = redis.Redis(host='localhost', port=6379)
redis_client.setex(f"council:{session_id}", 3600, json.dumps(session_data))

# Option 2: Use Database
from app.models import CouncilSession
session_record = CouncilSession(
    id=session_id,
    org_id=org_id,
    query=query,
    status="running",
    ...
)
await db.add(session_record)
```

### Cost Optimization

To minimize API costs:

1. Use `deliverable-only` mode for automated systems
2. Prefer faster models (Gemini 2.0 Flash, Perplexity Sonar)
3. Set reasonable token limits per provider
4. Cache results for similar queries
5. Monitor token usage per org

### Scalability

For high concurrency:

1. Increase pool of async workers
2. Implement request queuing
3. Add Redis cache for common responses
4. Monitor provider rate limits
5. Implement circuit breaker for provider failures

---

## Troubleshooting

### Council Hangs or Times Out

**Solution:** Check provider API status and rate limits
```bash
# Check OpenAI status
curl -s https://status.openai.com/api/v2/status.json | jq '.status.indicator'

# Check Perplexity status
# Monitor token usage in provider dashboards
```

### Wrong Provider Used

**Check:** Agent provider mapping and available API keys
```python
# Verify provider configuration
from app.services.council.config import AGENT_PROVIDER_MAPPING
print(AGENT_PROVIDER_MAPPING)

# Check available keys in database
SELECT provider, COUNT(*) FROM provider_keys WHERE org_id = 'org_demo' GROUP BY provider;
```

### WebSocket Connection Fails

**Causes:**
- CORS misconfiguration
- WebSocket proxy not configured
- Firewall blocking WebSocket port

**Solution:** Verify CORS in main.py and check proxy configuration

### Out of Memory

**Cause:** Large number of concurrent sessions stored in memory

**Solution:** Implement session cleanup or switch to Redis/database storage

---

## Next Steps

1. ✅ **Backend Integration:** Complete
2. 📋 **Frontend Integration:** Use provided React hook
3. 🧪 **Testing:** Run test scenarios above
4. 📊 **Monitoring:** Set up logging/alerting
5. 🚀 **Deployment:** Follow deployment checklist
6. 📚 **Documentation:** Update API docs with council endpoints

---

## Reference Documentation

- Architecture: `docs/architecture/COLLABORATION_ARCHITECTURE.md`
- Agents: `docs/architecture/COLLABORATION_AGENTS.md`
- Workflow: `docs/architecture/COLLABORATION_WORKFLOW.md`
- Implementation: `docs/architecture/COLLABORATION_IMPLEMENTATION.md`

---

## Support

For issues or questions:
1. Check logs: `docker logs syntra-backend`
2. Review provider dashboards for API status
3. Verify API keys are configured in database
4. Test with single provider first
5. Check WebSocket/CORS configuration
