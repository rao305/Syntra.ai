# Integrating v0-Generated UI with Phase 1 Features

This guide helps you integrate v0-generated code while preserving all Phase 1 functionality.

---

## Phase 1 Features to Preserve

When integrating v0 code, make sure these features remain intact:

### ✅ Core Functionality
1. **Router-based provider selection** - Automatically selects provider based on message
2. **Provider badges** - Shows which provider handled each message
3. **Scope toggle** - Private/Shared memory scope control
4. **Rate limit handling** - Shows 429 errors with Retry-After
5. **Error handling** - Displays API errors gracefully
6. **Thread management** - Creates/uses threads automatically
7. **API integration** - Uses `apiFetch()` with `x-org-id` header
8. **Audit trail** - All messages logged with hashes

### ✅ Current UI Components

**Threads Page** (`/app/threads/page.tsx`):
- Message display with provider badges
- Scope toggle (Private/Shared)
- Rate limit banner
- Error messages
- Input area with send button

**Settings Page** (`/app/settings/providers/page.tsx`):
- Provider configuration
- API key management
- Test connection buttons
- Usage statistics

**Thread Detail** (`/app/threads/[threadId]/page.tsx`):
- Message history
- Audit table

---

## Integration Steps

### Step 1: Copy v0-Generated Code

1. Open the v0.app link in your browser
2. Generate the component you want (chat UI, settings page, etc.)
3. Copy the generated code

### Step 2: Identify What to Replace

**For Threads Page:**
- ✅ Keep: All state management (`messages`, `threadId`, `scope`, `error`, etc.)
- ✅ Keep: `handleSendMessage()` function (all API calls)
- ✅ Keep: `apiFetch()` calls with `orgId`
- ✅ Keep: Provider badge logic
- ✅ Keep: Scope toggle logic
- ✅ Keep: Rate limit handling
- 🔄 Replace: UI markup/styling (divs, classes, layout)

**For Settings Page:**
- ✅ Keep: All state management
- ✅ Keep: `loadProviderStatuses()`, `handleSaveKey()`, `handleTestConnection()`
- ✅ Keep: `apiFetch()` calls
- 🔄 Replace: UI markup/styling

### Step 3: Integration Template

Here's a template for integrating v0 code into the threads page:

```typescript
'use client'

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { ApiError, apiFetch } from '@/lib/api'

// ✅ KEEP: All your types and constants
type Provider = 'perplexity' | 'openai' | 'gemini' | 'openrouter'
type ScopeOption = 'private' | 'shared'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  provider?: Provider
  timestamp: Date
  meta?: Record<string, any>
}

// ✅ KEEP: Provider colors and labels
const PROVIDER_COLORS: Record<Provider, string> = { /* ... */ }
const PROVIDER_LABELS: Record<Provider, string> = { /* ... */ }

export default function ThreadsPage() {
  // ✅ KEEP: All state management
  const { data: session, status } = useSession()
  const router = useRouter()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [threadId, setThreadId] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scope, setScope] = useState<ScopeOption>('private')
  const [rateLimitMessage, setRateLimitMessage] = useState<string | null>(null)
  const orgId = (session?.user as { orgId?: string } | undefined)?.orgId

  // ✅ KEEP: All useEffect hooks
  useEffect(() => { /* ... */ }, [status, router])

  // ✅ KEEP: handleSendMessage function (entire function)
  const handleSendMessage = async () => {
    // ... all your existing logic
  }

  // ✅ KEEP: handleKeyPress
  const handleKeyPress = (e: React.KeyboardEvent) => { /* ... */ }

  // ✅ KEEP: Loading and auth checks
  if (status === 'loading') { /* ... */ }
  if (!session) { return null }
  if (!orgId) { /* ... */ }

  return (
    // 🔄 REPLACE: This entire return block with v0-generated JSX
    // But make sure to:
    // 1. Use your state variables (messages, input, sending, error, etc.)
    // 2. Call your functions (handleSendMessage, handleKeyPress)
    // 3. Display provider badges from message.provider
    // 4. Show scope toggle
    // 5. Show rate limit banner
    // 6. Show error messages
  )
}
```

---

## Key Integration Points

### 1. Message Display

**Current:**
```typescript
{messages.map((message) => (
  <div className={...}>
    {message.provider && (
      <span className={PROVIDER_COLORS[message.provider]}>
        {PROVIDER_LABELS[message.provider]}
      </span>
    )}
    <p>{message.content}</p>
  </div>
))}
```

**v0 Integration:** Replace the div structure with v0's message component, but keep:
- `message.provider` check
- `PROVIDER_COLORS` and `PROVIDER_LABELS` usage
- `message.content` display

### 2. Input Area

**Current:**
```typescript
<textarea
  value={input}
  onChange={(e) => setInput(e.target.value)}
  onKeyPress={handleKeyPress}
  disabled={sending}
/>
<button onClick={handleSendMessage} disabled={!input.trim() || sending}>
  {sending ? 'Sending...' : 'Send'}
</button>
```

**v0 Integration:** Use v0's input component, but keep:
- `value={input}`
- `onChange={(e) => setInput(e.target.value)}`
- `onKeyPress={handleKeyPress}`
- `onClick={handleSendMessage}`
- `disabled` states

### 3. Scope Toggle

**Current:**
```typescript
<div className="mb-4 flex items-center gap-3">
  <span>Forward scope:</span>
  <button onClick={() => setScope('private')}>Private only</button>
  <button onClick={() => setScope('shared')}>Allow shared</button>
</div>
```

**v0 Integration:** Use v0's toggle/button group, but keep:
- `onClick={() => setScope('private')}`
- `onClick={() => setScope('shared')}`
- `scope === 'private'` conditional styling

### 4. Error & Rate Limit Banners

**Current:**
```typescript
{error && (
  <div className="mb-4 p-3 bg-red-50 border border-red-200">
    <p>{error}</p>
  </div>
)}
{rateLimitMessage && (
  <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200">
    <p>{rateLimitMessage}</p>
  </div>
)}
```

**v0 Integration:** Use v0's alert/banner component, but keep:
- `{error && ...}` conditional rendering
- `{rateLimitMessage && ...}` conditional rendering
- Error message display

---

## Checklist Before Replacing UI

Before replacing any UI code, verify:

- [ ] All state variables are preserved
- [ ] All `useEffect` hooks are kept
- [ ] `handleSendMessage()` function is unchanged
- [ ] `apiFetch()` calls use `orgId` parameter
- [ ] Provider badge logic is preserved
- [ ] Scope toggle functionality is kept
- [ ] Error handling is maintained
- [ ] Rate limit handling is preserved
- [ ] Loading states are handled
- [ ] Auth checks are in place

---

## Example: Integrating v0 Chat Component

If v0 generates a chat component like this:

```typescript
// v0-generated code
<div className="chat-container">
  {messages.map((msg) => (
    <div key={msg.id} className="message">
      <p>{msg.text}</p>
    </div>
  ))}
  <input 
    value={input}
    onChange={(e) => setInput(e.target.value)}
    onKeyPress={handleSend}
  />
</div>
```

**Your integration should be:**

```typescript
// Your integrated code
<div className="chat-container">
  {messages.map((message) => (
    <div key={message.id} className="message">
      {/* ✅ ADD: Provider badge */}
      {message.provider && (
        <span className={PROVIDER_COLORS[message.provider]}>
          {PROVIDER_LABELS[message.provider]}
        </span>
      )}
      <p>{message.content}</p>
      <span className="timestamp">
        {message.timestamp.toLocaleTimeString()}
      </span>
    </div>
  ))}
  {/* ✅ ADD: Error banner */}
  {error && <div className="error-banner">{error}</div>}
  {/* ✅ ADD: Rate limit banner */}
  {rateLimitMessage && <div className="rate-limit-banner">{rateLimitMessage}</div>}
  {/* ✅ ADD: Scope toggle */}
  <div className="scope-toggle">
    <button onClick={() => setScope('private')}>Private</button>
    <button onClick={() => setScope('shared')}>Shared</button>
  </div>
  <input 
    value={input}
    onChange={(e) => setInput(e.target.value)}
    onKeyPress={handleKeyPress}  {/* ✅ KEEP: Your handler */}
    disabled={sending}  {/* ✅ ADD: Disabled state */}
  />
  <button 
    onClick={handleSendMessage}  {/* ✅ KEEP: Your handler */}
    disabled={!input.trim() || sending}
  >
    {sending ? 'Sending...' : 'Send'}
  </button>
</div>
```

---

## Testing After Integration

After integrating v0 code, test:

1. ✅ Send a message → Should create thread and call router
2. ✅ Check provider badge → Should show correct provider
3. ✅ Toggle scope → Should change scope state
4. ✅ Hit rate limit → Should show banner
5. ✅ Check errors → Should display error messages
6. ✅ Verify API calls → Should include `x-org-id` header
7. ✅ Check audit → Should log entries with hashes

---

## Common Pitfalls

### ❌ Don't:
- Remove `apiFetch()` calls
- Remove `orgId` parameter
- Remove provider badge logic
- Remove scope toggle
- Remove error handling
- Remove rate limit handling
- Change function names (`handleSendMessage`, etc.)

### ✅ Do:
- Keep all state management
- Keep all API integration
- Keep all Phase 1 features
- Only replace UI markup/styling
- Test thoroughly after changes

---

## Need Help?

If you're stuck integrating v0 code:

1. **Share the v0-generated code** - I can help integrate it
2. **Point out specific issues** - What's not working?
3. **Ask about specific features** - Which Phase 1 feature is broken?

---

**Remember:** The goal is better UI, not removing functionality. All Phase 1 features must remain intact!

