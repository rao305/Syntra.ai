# DAC TypeScript Stack - Architecture

## System Architecture (ASCII)

```text
                         ┌──────────────────────────┐
                         │        Frontend         │
                         │  Next.js + Tailwind     │
                         │  - Chat UI              │
                         │  - Model switch badge   │
                         │  - Streaming renderer   │
                         └───────────┬─────────────┘
                                     │ HTTPS / SSE
                                     ▼
                        ┌────────────────────────────┐
                        │        DAC Gateway         │
                        │   /api/dac/chat            │
                        └───────────┬────────────────┘
                                     │
                                     ▼
                       ┌──────────────────────────────┐
                       │         DAC Router           │
                       │  - classifyTask()            │
                       │  - routeDAC()                │
                       │  - choose primary model      │
                       │  - optionally choose collab  │
                       └───────────┬──────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
          ┌─────────────────┐             ┌─────────────────┐
          │  Safety Layer   │             │ Prompt Compressor│
          │  - safetyCheck  │             │  - truncate      │
          │  - allow/deny   │             │  - summarize     │
          └────────┬────────┘             └────────┬────────┘
                   │                               │
                   └──────────────┬────────────────┘
                                  ▼
                       ┌──────────────────────────────┐
                       │  Provider Orchestration      │
                       │   callProvider()             │
                       │   - OpenAI / Anthropic       │
                       │   - Google / Groq / Local    │
                       └───────┬─────────┬────────────┘
                               │         │
                    ┌──────────┘         └───────────┐
                    ▼                                ▼
           ┌────────────────┐               ┌────────────────┐
           │ Primary Model  │               │ Collab Models  │
           │  (e.g. GPT)    │               │  (Claude, Gem) │
           └───────┬────────┘               └───────┬────────┘
                   │                                │
                   └──────────────┬─────────────────┘
                                  ▼
                       ┌──────────────────────────────┐
                       │     Synthesizer (LLM)        │
                       │  - Merge primary + collab    │
                       │  - Produce final answer      │
                       └───────────┬──────────────────┘
                                   ▼
                        ┌────────────────────────────┐
                        │      DAC Gateway          │
                        │   stream to frontend      │
                        └────────────────────────────┘
```

## Directory Structure

```
typescript/
├── backend/
│   ├── dac/
│   │   ├── types.ts              # Core type definitions
│   │   ├── models.ts             # Model registry
│   │   ├── classifyTask.ts       # Task classifier
│   │   ├── router.ts             # Main routing logic
│   │   ├── safety.ts             # Safety filtering
│   │   └── promptCompressor.ts   # Context compression
│   ├── api/
│   │   └── dacChat.ts            # Main chat handler
│   └── providers/
│       ├── openai.ts             # OpenAI adapter
│       ├── anthropic.ts          # Anthropic adapter
│       ├── google.ts             # Google/Gemini adapter
│       ├── groq.ts               # Groq adapter
│       └── local.ts              # Local model adapter
│
└── frontend/
    ├── app/
    │   └── chat/
    │       └── page.tsx          # Main chat page
    ├── components/
    │   ├── ModelSwitchIndicator.tsx  # Model status indicator
    │   └── ChatMessageBubble.tsx     # Message bubble component
    └── lib/
        └── api.ts                # Frontend API client
```

## Data Flow

### 1. Request Processing

```typescript
User Input
    ↓
Safety Check (filter harmful content)
    ↓
Task Classification (code/math/factual/creative/multimodal/chat)
    ↓
Model Selection (pick primary + optional collab models)
    ↓
Context Compression (if needed)
    ↓
Primary Model Call
    ↓
[Optional] Collaboration (refinement by secondary models)
    ↓
[Optional] Synthesis (merge multiple responses)
    ↓
Response Stream to Frontend
```

### 2. Safety Layer Flow

```typescript
runSafetyCheck()
    ↓
┌─ Self-harm keywords? → BLOCK
├─ Violence/terror? → BLOCK
├─ Sexual content (minors)? → BLOCK
├─ Ambiguous (hacking, etc)? → NEEDS_CLARIFICATION
└─ Safe → ALLOW
```

### 3. Prompt Compression Flow

```typescript
Message History (N turns)
    ↓
Token Count > Limit?
    ├─ NO → Return as-is
    └─ YES ↓
Keep last 6 recent turns
    ↓
Summarize earlier history with cheap model
    ↓
Replace old messages with summary
    ↓
Return compressed context
```

## Key Components

### Router (classifyTask + routeDAC)
- **Input**: User messages
- **Output**: TaskType + selected ModelConfig(s)
- **Logic**: Regex-based keyword matching for fast classification
- **Cost optimization**: Prefer cheaper/faster models for simple tasks

### Safety Layer (runSafetyCheck)
- **Input**: User message
- **Output**: SafetyVerdict (allow/block/needs_clarification)
- **Checks**: Self-harm, violence, illegal content, ambiguous requests

### Prompt Compressor (compressRequestContext)
- **Input**: Full conversation history
- **Output**: Compressed context within token limits
- **Strategy**: Keep recent turns + summarize older history

### Model Registry (MODELS)
- Centralized configuration for all available models
- Metadata: provider, strengths, cost tier, latency tier, max tokens

## Integration Points

### Backend → Python DAC
The TypeScript router can call the Python backend's DAC system prompts:

```typescript
import { DAC_SYSTEM_PROMPT } from './prompts/python-dac';

const response = await callProvider('openai', {
  model: 'gpt-4.1',
  system: DAC_SYSTEM_PROMPT, // from Python implementation
  messages: compressedContext.messages
});
```

### Frontend → Backend API
```typescript
// Frontend calls TypeScript backend
const response = await fetch('/api/dac/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ messages })
});

// SSE for streaming
const eventSource = new EventSource('/api/dac/chat/stream');
eventSource.on message((event) => {
  const { type, data } = JSON.parse(event.data);
  // Update UI based on routing events
});
```

## Performance Characteristics

| Component | Latency | Purpose |
|-----------|---------|---------|
| classifyTask | <5ms | Fast regex-based classification |
| runSafetyCheck | <10ms | Keyword-based filtering |
| routeDAC | <20ms | Model selection logic |
| compressRequestContext | ~100-500ms | LLM-based summarization (if needed) |
| Primary model call | 500-3000ms | Actual LLM API call |
| Collaboration | +1000-2000ms | Additional model calls |
| Synthesis | +500-1500ms | Final merge step |

## Deployment Options

### Option 1: Serverless (Vercel/Netlify)
- Deploy frontend + backend as Next.js API routes
- Edge functions for fast routing decisions
- Serverless functions for LLM calls

### Option 2: Node.js Server
- Express/Fastify server for backend
- Next.js for frontend (separate or integrated)
- WebSocket/SSE for streaming

### Option 3: Hybrid
- TypeScript router on edge (fast classification)
- Python backend for heavy processing
- Frontend on CDN

## Environment Variables

```bash
# LLM Provider API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
GROQ_API_KEY=...

# DAC Configuration
DAC_ENABLE_COLLAB=true
DAC_MAX_COLLAB_MODELS=3
DAC_DEFAULT_MODEL=gpt-4.1-mini

# Safety
DAC_SAFETY_MODE=strict  # strict | normal | permissive

# Performance
DAC_MAX_TOKENS=4096
DAC_RESERVE_TOKENS=1024
```

## Next Steps

1. **Implement Provider Adapters**: Create SDK wrappers for each provider
2. **Add Streaming Support**: Implement SSE/WebSocket for real-time updates
3. **Cost Tracking**: Add usage metrics and cost estimation
4. **Testing**: Unit tests for router, safety, compression
5. **Monitoring**: Add logging and error tracking
