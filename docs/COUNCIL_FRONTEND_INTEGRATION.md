# Council Orchestration - Frontend Integration Guide

**Date:** 2025-12-12
**Status:** Ready for Integration

---

## Overview

This guide explains how to integrate the Council Orchestration UI components into your existing Syntra frontend chat interface.

---

## Components

### 1. `CouncilOrchestration` (Core Component)

**Location:** `frontend/components/collaboration/council-orchestration.tsx`

The main orchestration UI showing:
- Animated phase list with progress tracking
- Real-time agent execution timeline
- Phase output display on selection
- Show Process collapsible panel
- Final answer display

**Props:**
```typescript
interface CouncilOrchestrationProps {
  query: string              // The user's query/task
  orgId: string              // Organization ID
  onComplete: (output: string) => void  // Callback when complete
  onClose: () => void        // Callback when user closes
}
```

**Usage:**
```tsx
<CouncilOrchestration
  query={userQuery}
  orgId={orgId}
  onComplete={(output) => console.log('Final answer:', output)}
  onClose={() => setShowCouncil(false)}
/>
```

### 2. `CollaborationButton`

**Location:** `frontend/components/collaboration/collaboration-button.tsx`

Simple button wrapper that opens the Council Orchestration in a modal dialog.

**Props:**
```typescript
interface CollaborationButtonProps {
  query: string
  orgId: string
  onComplete: (output: string) => void
  disabled?: boolean
  className?: string
}
```

**Usage:**
```tsx
<CollaborationButton
  query="Create a FastAPI service"
  orgId={orgId}
  onComplete={(output) => handleFinalAnswer(output)}
  disabled={!query.trim()}
/>
```

### 3. `useCouncilOrchestrator` (Hook)

**Location:** `frontend/components/collaboration/use-council-orchestrator.ts`

React hook for managing council orchestration state and API calls.

**State:**
```typescript
{
  sessionId: string | null
  status: 'idle' | 'pending' | 'running' | 'success' | 'error'
  currentPhase: Phase | null
  output: string | null
  error: string | null
  executionTimeMs: number | null
  isRunning: boolean
}
```

**Methods:**
```typescript
const {
  // State
  status,
  currentPhase,
  output,
  error,
  isRunning,

  // Actions
  startCouncil(query, orgId, outputMode?, preferredProviders?)
  cancelCouncil(orgId)
  reset()
} = useCouncilOrchestrator()
```

**Usage:**
```tsx
const council = useCouncilOrchestrator()

const handleStart = async () => {
  await council.startCouncil(
    query,
    orgId,
    'deliverable-ownership',
    { researcher: 'perplexity' }
  )
}

return (
  <>
    <button onClick={handleStart}>Start Council</button>
    <p>Status: {council.status}</p>
    <p>Current Phase: {council.currentPhase}</p>
  </>
)
```

### 4. `CouncilChatIntegration`

**Location:** `frontend/components/collaboration/council-chat-integration.tsx`

High-level integration component for chat UI.

**Sub-components:**
- `CouncilChatIntegration` - Modal wrapper
- `CollaborationInputExtension` - Chat input button
- `CouncilFinalAnswer` - Final answer display

---

## Integration Steps

### Step 1: Replace Mode Selector

**Before (Remove):**
```tsx
<select value={mode} onChange={(e) => setMode(e.target.value)}>
  <option value="auto">Auto Collaboration</option>
  <option value="manual">Manual Collaboration</option>
</select>
```

**After (Add):**
```tsx
import { CollaborationInputExtension } from '@/components/collaboration/council-chat-integration'

<CollaborationInputExtension
  isLoading={isLoading}
  onCollaborationClick={() => setShowCouncil(true)}
/>
```

### Step 2: Add Modal Integration

In your chat component:

```tsx
'use client'

import { useState } from 'react'
import { CouncilChatIntegration, CouncilFinalAnswer } from '@/components/collaboration/council-chat-integration'

export function ChatThread() {
  const [messages, setMessages] = useState([])
  const [query, setQuery] = useState('')
  const [showCouncil, setShowCouncil] = useState(false)

  const handleCollaborationClick = () => {
    if (query.trim()) {
      setShowCouncil(true)
    }
  }

  const handleFinalAnswer = (answer: string) => {
    // Add the final answer as a message in the chat
    const councilMessage = {
      id: Date.now(),
      role: 'assistant',
      content: answer,
      type: 'council', // Mark as council output
    }

    setMessages([...messages, councilMessage])
    setShowCouncil(false)
    setQuery('')
  }

  return (
    <div>
      {/* Chat Messages */}
      <div className="space-y-4">
        {messages.map((msg) => (
          <div key={msg.id}>
            {msg.type === 'council' ? (
              <CouncilFinalAnswer answer={msg.content} />
            ) : (
              <div>{msg.content}</div>
            )}
          </div>
        ))}
      </div>

      {/* Chat Input */}
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask the council..."
        />
        <CollaborationInputExtension
          isLoading={false}
          onCollaborationClick={handleCollaborationClick}
        />
      </div>

      {/* Council Modal */}
      {showCouncil && (
        <CouncilChatIntegration
          query={query}
          orgId={orgId}
          onFinalAnswer={handleFinalAnswer}
          onCancel={() => setShowCouncil(false)}
        />
      )}
    </div>
  )
}
```

### Step 3: Update Chat Message Rendering

Add support for rendering council outputs:

```tsx
function renderMessage(message: Message) {
  if (message.type === 'council') {
    return <CouncilFinalAnswer answer={message.content} />
  }

  // Regular message rendering
  return <div>{message.content}</div>
}
```

---

## UI Behavior

### Phase Progression

The UI shows phases in order with visual indicators:

1. **Phase 1 (Parallel):** 5 agents execute simultaneously
   - Optimizer Agent
   - Red Teamer Agent
   - Data Engineer Agent
   - Researcher Agent
   - Architect Agent

2. **Phase 2 (Sequential):** Debate Synthesizer
   - Merges all agent outputs
   - Resolves conflicts
   - Creates ownership map

3. **Phase 3 (Sequential):** Judge Agent
   - Validates deliverable
   - Issues verdict
   - Produces final output

4. **Complete:** Final Answer
   - Display in main output panel
   - Copy to clipboard option
   - Close and return to chat

### Status Indicators

- ⚪ **Pending:** Task waiting to start (gray dot)
- 🟢 **Running:** Task currently executing (green pulse)
- 🟢 **Complete:** Task finished (solid green dot)

### Timing Display

Each agent shows execution time:
```
Optimizer Agent              17.7s
Red Teamer Agent            18.4s
Data Engineer Agent         16.4s
```

### Show Process Panel

Collapsible right panel showing:
- Each agent's details
- Full output preview
- Expandable sections per agent

---

## API Response Handling

The components automatically handle:

```typescript
// Start execution
POST /api/council/orchestrate

// Response
{
  "session_id": "uuid",
  "status": "pending",
  "current_phase": "Initializing..."
}

// WebSocket updates
{
  "type": "progress",
  "current_phase": "Running 5 specialist agents in parallel..."
}

{
  "type": "complete",
  "status": "success",
  "execution_time_ms": 25000,
  "output": "... final deliverable ..."
}
```

---

## Styling & Theming

All components support light/dark mode via Tailwind:

```css
/* Light Mode */
bg-white
text-slate-900
border-slate-200

/* Dark Mode */
dark:bg-slate-800
dark:text-slate-100
dark:border-slate-700
```

### Customization

Override colors via CSS variables or Tailwind config:

```tsx
<CouncilOrchestration
  className="[&_.agent-item]:bg-blue-50"
/>
```

---

## Error Handling

The components handle errors gracefully:

```typescript
if (council.error) {
  return (
    <div className="p-4 bg-red-50 border border-red-200 rounded">
      <p className="text-red-900 font-semibold">Error</p>
      <p className="text-red-700 text-sm">{council.error}</p>
      <button onClick={() => council.reset()}>Retry</button>
    </div>
  )
}
```

---

## Performance Optimization

The components are optimized for:

- **Parallel rendering:** Phase list doesn't block output panel
- **Efficient WebSocket:** Only updates changed state
- **Lazy rendering:** Show Process panel only when needed
- **Memoization:** Agent list items don't re-render unnecessarily

---

## Accessibility

Components include:

- Keyboard navigation (Tab, Enter)
- ARIA labels for screen readers
- Focus management in modal
- Clear visual feedback for interactive elements

---

## Mobile Responsiveness

On mobile devices:

- Modal takes full screen
- Phase list stacks vertically
- Output panel scrollable
- Show Process panel slides up from bottom

```tsx
// On mobile
<CouncilOrchestration
  className="max-w-full"
/>

// Responsive layout
<div className="flex flex-col md:flex-row gap-4">
  {/* Phase list - full width on mobile */}
  {/* Output panel - full width on mobile */}
</div>
```

---

## Advanced Usage

### Custom Output Modes

```tsx
<CouncilOrchestration
  query={query}
  orgId={orgId}
  outputMode="audit"  // Or "full-transcript"
  onComplete={handleComplete}
/>
```

### Provider Selection

```tsx
const handleStart = async () => {
  await council.startCouncil(
    query,
    orgId,
    'deliverable-ownership',
    {
      architect: 'openai',
      researcher: 'perplexity',  // Use Perplexity for research
      red_teamer: 'gemini',      // Use Gemini for threat modeling
    }
  )
}
```

### Custom Completion Handler

```tsx
const handleFinalAnswer = (answer: string) => {
  // Store in database
  saveCouncilOutput(answer)

  // Send to chat
  appendMessage({ role: 'assistant', content: answer })

  // Analytics
  trackCouncilExecution(council.executionTimeMs)

  // Close modal
  setShowCouncil(false)
}
```

---

## Testing

### Unit Tests

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import { CouncilOrchestration } from '@/components/collaboration/council-orchestration'

describe('CouncilOrchestration', () => {
  it('renders phase list', () => {
    render(
      <CouncilOrchestration
        query="test"
        orgId="org_test"
        onComplete={jest.fn()}
        onClose={jest.fn()}
      />
    )

    expect(screen.getByText('Optimizer Agent')).toBeInTheDocument()
  })

  it('shows final answer when complete', async () => {
    const onComplete = jest.fn()
    render(
      <CouncilOrchestration
        query="test"
        orgId="org_test"
        onComplete={onComplete}
        onClose={jest.fn()}
      />
    )

    // WebSocket simulation would happen here

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalled()
    })
  })
})
```

### Integration Tests

```tsx
// Test with actual WebSocket
it('connects to council orchestration endpoint', async () => {
  const mockFetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        session_id: 'test-session',
        status: 'pending'
      })
    })
  )

  global.fetch = mockFetch

  const council = useCouncilOrchestrator()
  await council.startCouncil('test query', 'org_test')

  expect(mockFetch).toHaveBeenCalledWith('/api/council/orchestrate', expect.any(Object))
})
```

---

## Troubleshooting

### WebSocket Connection Fails

**Issue:** "WebSocket connection error"

**Solution:**
```tsx
// Check CORS configuration
// Verify WebSocket endpoint is accessible
// Check firewall/proxy settings

// Add error logging
wsRef.current.onerror = (event) => {
  console.error('WebSocket error:', event)
  console.log('Attempting reconnection in 2s...')
  setTimeout(connectWebSocket, 2000)
}
```

### Final Answer Not Displaying

**Issue:** Modal closes but answer doesn't appear in chat

**Solution:**
```tsx
// Ensure onComplete callback is called BEFORE onClose
const handleComplete = (output: string) => {
  setFinalAnswer(output)  // Store immediately
  // Modal closes after, then final answer displays
}
```

### Execution Times Wrong

**Issue:** Times don't match server logs

**Solution:**
```tsx
// Times are client-side estimates
// Server returns actual times in WebSocket message
const handleComplete = (message: any) => {
  const actualTime = message.execution_time_ms  // Use this
  console.log('Actual execution time:', actualTime)
}
```

---

## Next Steps

1. ✅ Copy component files to `frontend/components/collaboration/`
2. Update chat interface to use `CollaborationInputExtension`
3. Implement `handleFinalAnswer` in chat logic
4. Test with different queries and providers
5. Gather user feedback on UX
6. Iterate on styling/animations as needed

---

## Support

For questions or issues:
1. Check backend logs: `docker logs syntra-backend`
2. Check browser console for frontend errors
3. Verify API keys are configured
4. Test with simple queries first
5. Check WebSocket connection in DevTools

---

## API Reference

### POST /api/council/orchestrate

Start a council orchestration session.

**Headers:**
```
x-org-id: org_id
Content-Type: application/json
```

**Body:**
```json
{
  "query": "Create a FastAPI service",
  "output_mode": "deliverable-ownership",
  "preferred_providers": {
    "researcher": "perplexity"
  }
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "status": "pending",
  "current_phase": "Initializing..."
}
```

### GET /api/council/orchestrate/{session_id}

Get current status of a council session.

**Response:**
```json
{
  "session_id": "uuid",
  "status": "running",
  "output": null,
  "error": null,
  "execution_time_ms": 5000,
  "current_phase": "Running synthesizer..."
}
```

### WS /api/council/ws/{session_id}

WebSocket connection for real-time updates.

**Messages:**
```json
{"type": "status", "session_id": "...", "status": "running"}
{"type": "progress", "current_phase": "..."}
{"type": "complete", "status": "success", "output": "..."}
{"type": "error", "error": "..."}
```

---

## Summary

The Council Orchestration UI provides:
- ✅ Real-time phase progression visualization
- ✅ Individual phase output inspection
- ✅ Clean, animated final answer display
- ✅ Multi-provider support with auto-selection
- ✅ Full audit trail with "Show Process"
- ✅ Mobile responsive design
- ✅ Light/dark mode support
- ✅ Accessible keyboard navigation

Ready for production use! 🚀
