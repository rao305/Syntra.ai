# Context Debugging Playbook

## 1. Symptoms Table

| Symptom | Root Cause | Where to Check | Fix |
|---------|-----------|----------------|-----|
| Wrong entity answered (e.g., "John Doe" instead of "Donald Trump") | History missing from context | Logs: `short_term_history_len=0` | Thread overwritten or turns not loaded |
| Follow-up question treated as isolated | Context builder not seeing previous turns | Logs: `Conversation history turns: 0` | `get_history()` returning empty or thread not found |
| History unexpectedly empty | Context builder using wrong function | Code: Using `get_or_create_thread()` in read path | Use `get_thread()` or `get_history()` |
| Context flickers between turns | Race condition in saving | Logs: Turn count inconsistent | Save turns immediately, not in background |
| Rewriter destroys context | Rewriter output invalid or missing | Logs: Rewriter error or empty output | Check rewriter return type and fallback |
| Thread ID changes between requests | API not reusing thread_id | Logs: Different `thread_id` values | Pass `thread_id` from request consistently |
| Turns disappear after request | Thread object replaced | Logs: Different `obj_id` for same `thread_id` | Thread being recreated instead of reused |
| Memory snippet replaces history | Supermemory integration bug | Logs: Only memory in messages, no history | Memory should supplement, not replace history |
| Rewriter doesn't resolve pronouns | Rewriter not receiving history | Logs: Rewriter called without history | Pass `recent_history` to rewriter |
| DB fallback not loading | Database query failing | Logs: "No messages found in DB" | Check DB connection and query logic |

---

## 2. Quick Debug Checklist (10 Steps)

### Step 1: Check Thread ID Continuity

```bash
# In backend logs, search for thread_id
grep "thread_id=" /path/to/logs | tail -20

# Expected: Same thread_id for both requests
# ❌ BAD: thread_id=abc-123 (request 1), thread_id=def-456 (request 2)
# ✅ GOOD: thread_id=abc-123 (request 1), thread_id=abc-123 (request 2)
```

**Fix if broken:** Ensure API endpoint passes `thread_id` from request, doesn't generate new one.

### Step 2: Check Short-Term History Length

```bash
# In backend logs, search for history length
grep "short_term_history_len\|Conversation history turns" /path/to/logs | tail -10

# Expected: Second request shows >= 2 turns
# ❌ BAD: short_term_history_len=0 (second request)
# ✅ GOOD: short_term_history_len=2 (second request)
```

**Fix if broken:** Check `get_history()` is being called correctly, thread exists in store.

### Step 3: Check Messages Preview Before Provider Call

```bash
# In backend logs, search for messages preview
grep "Messages array preview\|Messages preview" /path/to/logs | tail -30

# Expected: Second request includes previous Q&A
# ❌ BAD: Only current user message in preview
# ✅ GOOD: Previous user + assistant + current user in preview
```

**Fix if broken:** Context builder not including history in messages array.

### Step 4: Check THREADS Keys and Lengths

```python
# Add temporary debug code
from app.services.threads_store import THREADS

# In context builder or API endpoint
print(f"[DEBUG] THREADS keys: {list(THREADS.keys())}")
for thread_id, thread in THREADS.items():
    print(f"[DEBUG] Thread {thread_id}: {len(thread.turns)} turns")
```

**Expected:** Thread exists with correct number of turns.

**Fix if broken:** Thread not being saved or being cleared.

### Step 5: Check Thread Object Identity

```python
# Add temporary debug code
from app.services.threads_store import get_thread

# In context builder
thread = get_thread(thread_id)
if thread:
    print(f"[DEBUG] Thread obj_id: {id(thread)}, turns: {len(thread.turns)}")
```

**Expected:** Same `obj_id` across requests for same `thread_id`.

**Fix if broken:** Thread being recreated instead of reused.

### Step 6: Check Whether Rewriter Rewrote Correctly

```bash
# In backend logs, search for rewriter output
grep "rewritten\|LLM rewrite\|Query rewritten" /path/to/logs | tail -10

# Expected: Rewriter output mentions correct entity
# ❌ BAD: "who are his children" → "who are his children" (not rewritten)
# ✅ GOOD: "who are his children" → "Who are Donald Trump's children?"
```

**Fix if broken:** Rewriter not receiving history or failing silently.

### Step 7: Check That Supermemory Didn't Override Short-Term History

```bash
# In backend logs, check messages array
grep -A 10 "Messages array preview" /path/to/logs | tail -20

# Expected: Both memory snippet AND history present
# ❌ BAD: Only memory snippet, no history
# ✅ GOOD: Memory snippet + history turns
```

**Fix if broken:** Supermemory integration replacing history instead of supplementing.

### Step 8: Check Turn Count After Each Request

```python
# Add temporary debug code
from app.services.threads_store import get_thread

# After saving turns
thread = get_thread(thread_id)
print(f"[DEBUG] After request: thread has {len(thread.turns)} turns")
```

**Expected:** Turn count increases by 2 per request (user + assistant).

**Fix if broken:** Turns not being saved or being cleared.

### Step 9: Check for Thread Overwriting

```python
# Add temporary debug code in add_turn
def add_turn(thread_id: str, turn: Turn) -> None:
    thread_before = get_thread(thread_id)
    if thread_before:
        print(f"[DEBUG] Before add_turn: obj_id={id(thread_before)}, turns={len(thread_before.turns)}")
    
    thread = get_or_create_thread(thread_id)
    
    if thread_before and thread is not thread_before:
        print(f"[ERROR] Thread object replaced! Old obj_id={id(thread_before)}, New obj_id={id(thread)}")
    
    thread.turns.append(turn)
    print(f"[DEBUG] After add_turn: obj_id={id(thread)}, turns={len(thread.turns)}")
```

**Expected:** Same thread object before and after.

**Fix if broken:** `get_or_create_thread()` creating new thread when one exists.

### Step 10: Check Context Builder Call Order

```python
# Add temporary debug code
async def build_contextual_messages(...):
    print(f"[DEBUG] build_contextual_messages called")
    print(f"[DEBUG] Loading history FIRST...")
    history = get_history(thread_id)  # Should be FIRST
    print(f"[DEBUG] History loaded: {len(history)} turns")
    # ... rest of function
```

**Expected:** History loaded before processing current message.

**Fix if broken:** Reorder context builder to load history first.

---

## 3. Debug Tools

### Print Thread Store Contents

```python
# Add to any function for debugging
from app.services.threads_store import THREADS

def debug_thread_store():
    print(f"\n{'='*60}")
    print(f"THREAD STORE DEBUG")
    print(f"{'='*60}")
    print(f"Total threads: {len(THREADS)}")
    for thread_id, thread in THREADS.items():
        print(f"\nThread ID: {thread_id}")
        print(f"  Object ID: {id(thread)}")
        print(f"  Turns: {len(thread.turns)}")
        for i, turn in enumerate(thread.turns):
            print(f"    [{i}] {turn.role}: {turn.content[:50]}...")
    print(f"{'='*60}\n")
```

### Print Thread Object Identity

```python
from app.services.threads_store import get_thread

def debug_thread_identity(thread_id: str):
    thread = get_thread(thread_id)
    if thread:
        print(f"Thread {thread_id}:")
        print(f"  Object ID: {id(thread)}")
        print(f"  Turns: {len(thread.turns)}")
        print(f"  Thread ID: {thread.thread_id}")
    else:
        print(f"Thread {thread_id}: NOT FOUND")
```

### Print Turn Lengths

```python
from app.services.threads_store import get_history

def debug_turn_lengths(thread_id: str):
    history = get_history(thread_id, max_turns=20)
    print(f"Thread {thread_id}: {len(history)} turns in history")
    for i, turn in enumerate(history):
        print(f"  [{i}] {turn.role}: {len(turn.content)} chars")
```

### Print Messages Preview

```python
# In context builder, after building messages
def debug_messages_preview(messages: List[Dict[str, str]]):
    print(f"\n{'='*60}")
    print(f"MESSAGES PREVIEW")
    print(f"{'='*60}")
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        preview = content[:100] + "..." if len(content) > 100 else content
        print(f"[{i}] {role}: {preview}")
    print(f"{'='*60}\n")
```

### Check Context Builder Input/Output

```python
# Add to context builder
async def build_contextual_messages(...):
    print(f"[CTX DEBUG] Input:")
    print(f"  thread_id: {thread_id}")
    print(f"  latest_user_message: {latest_user_message[:50]}...")
    
    history = get_history(thread_id)
    print(f"[CTX DEBUG] History loaded: {len(history)} turns")
    
    # ... build messages ...
    
    print(f"[CTX DEBUG] Output:")
    print(f"  Total messages: {len(messages)}")
    print(f"  History turns: {len(history)}")
    print(f"  Memory snippet: {memory_snippet is not None}")
    
    return result
```

---

## 4. Known Failure Modes

### Failure Mode 1: The Original Trump/John Doe Bug

**Symptoms:**
- First request: "Who is Donald Trump?" → Correct answer
- Second request: "who are his children" → Answers about "John Doe" or random person

**Root Cause:**
- Context builder finding 0 turns on second request
- Thread store being overwritten or cleared between requests

**Detection:**
```bash
# Check logs
grep "short_term_history_len\|turns_count" /path/to/logs

# Should see: short_term_history_len=0 (WRONG)
# Should see: short_term_history_len=2 (CORRECT)
```

**Fix:**
- Ensure `get_or_create_thread()` reuses existing threads
- Ensure `get_history()` uses `get_thread()` (read-only)
- Ensure turns are saved immediately (not deferred)

### Failure Mode 2: Thread Overwriting

**Symptoms:**
- Logs show `turns_count=0` after saving turns
- Different `obj_id` for same `thread_id` across requests

**Root Cause:**
- `THREADS[thread_id] = Thread(...)` overwriting existing thread
- `get_or_create_thread()` creating new thread when one exists

**Detection:**
```python
# Check object identity
thread1 = get_thread(thread_id)  # Request 1
# ... save turns ...
thread2 = get_thread(thread_id)  # Request 2
if thread1 is not thread2:
    print("ERROR: Thread object replaced!")
```

**Fix:**
- Use `get_or_create_thread()` which checks for existing thread
- Never do `THREADS[thread_id] = Thread(...)` directly

### Failure Mode 3: Thread Shadowing

**Symptoms:**
- Thread store appears empty even though turns were saved
- `THREADS` dict has different keys than expected

**Root Cause:**
- Local variable `THREADS = {}` shadowing module-level dict
- Function creating new dict instead of using module-level

**Detection:**
```python
# Check if THREADS is module-level
import app.services.threads_store as ts
print(f"Module-level THREADS: {id(ts.THREADS)}")

# In suspicious function
print(f"Local THREADS: {id(THREADS)}")  # Should be same
```

**Fix:**
- Remove local `THREADS` variable
- Always import from module: `from app.services.threads_store import THREADS`

### Failure Mode 4: Turns Clearing

**Symptoms:**
- Turn count decreases between requests
- History suddenly empty

**Root Cause:**
- `thread.turns = []` being called accidentally
- `thread.turns.clear()` in normal flow

**Detection:**
```python
# Add logging to detect clearing
def add_turn(thread_id: str, turn: Turn):
    thread = get_thread(thread_id)
    if thread and len(thread.turns) == 0:
        print(f"[WARNING] Thread {thread_id} has 0 turns before add_turn")
    # ...
```

**Fix:**
- Remove any `thread.turns = []` or `thread.turns.clear()` calls
- Only use `clear_thread()` for explicit reset actions

### Failure Mode 5: DB Fallback Not Loading

**Symptoms:**
- In-memory store empty, but DB has messages
- Logs show "No messages found in DB"

**Root Cause:**
- DB query failing silently
- Wrong `thread_id` in DB query
- RLS (Row Level Security) blocking query

**Detection:**
```python
# Check DB query
prior_messages = await _get_recent_messages(db, thread_id)
print(f"DB returned {len(prior_messages)} messages for thread {thread_id}")
```

**Fix:**
- Check DB connection
- Verify RLS context is set correctly
- Check `thread_id` format matches DB format

### Failure Mode 6: Races in Async Tasks

**Symptoms:**
- Turn count inconsistent
- Some turns missing

**Root Cause:**
- Turns saved in background task after response
- Race condition between save and next request

**Detection:**
```python
# Check save timing
print(f"[DEBUG] Saving turn BEFORE streaming")
add_turn(thread_id, user_turn)  # Should be BEFORE

# Stream response
async for chunk in stream():
    yield chunk

print(f"[DEBUG] Saving turn AFTER streaming")
add_turn(thread_id, assistant_turn)  # Should be AFTER
```

**Fix:**
- Save user turn BEFORE streaming starts
- Save assistant turn AFTER streaming completes (but immediately, not in background)

### Failure Mode 7: Wrong Rewriter Return Shape

**Symptoms:**
- Rewriter error: `'str' object has no attribute 'get'`
- Rewriter output not being used

**Root Cause:**
- Rewriter returning string when dict expected (or vice versa)
- Caller expecting different return type

**Detection:**
```python
# Check rewriter return type
rewritten = await rewriter.rewrite(...)
print(f"Rewriter returned type: {type(rewritten)}")
print(f"Rewriter returned value: {rewritten}")
```

**Fix:**
- Check rewriter function signature
- Ensure return type matches caller expectations
- Add type hints and validation

---

## 5. How to Reproduce Bugs

### Reproducing the Trump/John Doe Bug

```bash
# 1. Start backend
cd backend
source venv/bin/activate
python -m uvicorn main:app --reload --port 8000

# 2. Send first request
curl -X POST http://localhost:8000/api/threads/new/messages/stream \
  -H "Content-Type: application/json" \
  -H "X-Org-Id: org_demo" \
  -d '{"content": "Who is Donald Trump?", "role": "user"}'

# Note the thread_id from response headers (x-thread-id)

# 3. Send second request with SAME thread_id
curl -X POST http://localhost:8000/api/threads/{thread_id}/messages/stream \
  -H "Content-Type: application/json" \
  -H "X-Org-Id: org_demo" \
  -d '{"content": "who are his children", "role": "user"}'

# 4. Check response - should mention Trump's children, not John Doe
```

### Reproducing Thread Overwriting

```python
# Add to test or debug script
from app.services.threads_store import THREADS, add_turn, get_thread, Turn

thread_id = "test-thread-overwrite"

# Request 1
add_turn(thread_id, Turn(role="user", content="Message 1"))
thread1 = get_thread(thread_id)
print(f"After request 1: obj_id={id(thread1)}, turns={len(thread1.turns)}")

# Simulate bug: overwrite thread
THREADS[thread_id] = Thread(thread_id=thread_id)  # BAD: Overwrites

# Request 2
thread2 = get_thread(thread_id)
print(f"After overwrite: obj_id={id(thread2)}, turns={len(thread2.turns)}")

# Should see: turns=0 (WRONG - lost previous turn)
```

### Reproducing Context Builder Not Seeing History

```python
# Add to test
from app.services.threads_store import add_turn, Turn
from app.services.context_builder import ContextBuilder

thread_id = "test-context-builder"
cb = ContextBuilder()

# Pre-populate with turns
add_turn(thread_id, Turn(role="user", content="Who is Donald Trump?"))
add_turn(thread_id, Turn(role="assistant", content="Donald Trump is..."))

# Build context
result = await cb.build_contextual_messages(
    thread_id=thread_id,
    latest_user_message="who are his children",
    # ...
)

# Check if history included
print(f"History turns: {len(result.short_term_history)}")
# Should be 2, not 0
```

---

## 6. How to Fix Each Failure Mode

### Fix 1: Thread Overwriting

**Problem:** Thread object being replaced instead of reused.

**Solution:**
```python
# ❌ WRONG
def bad_function(thread_id: str):
    THREADS[thread_id] = Thread(thread_id=thread_id)  # Overwrites

# ✅ CORRECT
def good_function(thread_id: str):
    thread = get_or_create_thread(thread_id)  # Reuses if exists
    # Use thread...
```

### Fix 2: Context Builder Not Loading History

**Problem:** Context builder using wrong function or wrong order.

**Solution:**
```python
# ❌ WRONG
async def bad_build_context(thread_id: str, message: str):
    messages = [{"role": "user", "content": message}]  # Current first
    history = get_history(thread_id)  # History after - WRONG ORDER
    messages = history + messages

# ✅ CORRECT
async def good_build_context(thread_id: str, message: str):
    history = get_history(thread_id)  # History FIRST
    messages = []
    # ... add system prompts ...
    for turn in history:  # Previous turns
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": message})  # Current last
```

### Fix 3: Turns Not Being Saved

**Problem:** Turns saved in background task or not saved at all.

**Solution:**
```python
# ❌ WRONG
async def bad_add_message(thread_id: str, content: str):
    # Stream response
    async for chunk in stream():
        yield chunk
    
    # Save in background (too late!)
    asyncio.create_task(save_to_db(thread_id, content))

# ✅ CORRECT
async def good_add_message(thread_id: str, content: str):
    # Save user message IMMEDIATELY
    add_turn(thread_id, Turn(role="user", content=content))
    
    # Stream response
    response_content = ""
    async for chunk in stream():
        yield chunk
        response_content += chunk
    
    # Save assistant message IMMEDIATELY after streaming
    add_turn(thread_id, Turn(role="assistant", content=response_content))
```

### Fix 4: Rewriter Not Receiving Context

**Problem:** Rewriter only seeing current message, not history.

**Solution:**
```python
# ❌ WRONG
async def bad_rewrite(message: str):
    return await rewriter.rewrite(message)  # No history

# ✅ CORRECT
async def good_rewrite(thread_id: str, message: str):
    history = get_history(thread_id)  # Load history
    memory = await get_memory(thread_id)  # Load memory
    return await rewriter.rewrite(
        latest_user_message=message,
        recent_history=history,  # Pass history
        memory_snippet=memory  # Pass memory
    )
```

### Fix 5: Supermemory Replacing History

**Problem:** Memory snippet used instead of history.

**Solution:**
```python
# ❌ WRONG
if memory_snippet:
    messages.append({"role": "system", "content": memory_snippet})
    # Missing history - WRONG

# ✅ CORRECT
# Add memory snippet
if memory_snippet:
    messages.append({"role": "system", "content": f"Memory: {memory_snippet}"})

# Add history (BOTH, not either/or)
for turn in history_turns:
    messages.append({"role": turn.role, "content": turn.content})
```

---

## 7. Emergency Debugging Script

Save this as `debug_context.py` and run when context issues occur:

```python
#!/usr/bin/env python3
"""Emergency context debugging script."""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.threads_store import THREADS, get_thread, get_history

def debug_all_threads():
    print(f"\n{'='*80}")
    print(f"CONTEXT SYSTEM DEBUG REPORT")
    print(f"{'='*80}\n")
    
    print(f"Total threads in store: {len(THREADS)}\n")
    
    if not THREADS:
        print("⚠️  WARNING: THREADS store is empty!")
        return
    
    for thread_id, thread in THREADS.items():
        print(f"Thread ID: {thread_id}")
        print(f"  Object ID: {id(thread)}")
        print(f"  Turns: {len(thread.turns)}")
        
        if thread.turns:
            print(f"  Turn breakdown:")
            user_count = sum(1 for t in thread.turns if t.role == "user")
            assistant_count = sum(1 for t in thread.turns if t.role == "assistant")
            print(f"    User: {user_count}, Assistant: {assistant_count}")
            
            print(f"  Recent turns:")
            for i, turn in enumerate(thread.turns[-5:], start=max(0, len(thread.turns)-5)):
                preview = turn.content[:60] + "..." if len(turn.content) > 60 else turn.content
                print(f"    [{i}] {turn.role}: {preview}")
        else:
            print(f"  ⚠️  WARNING: Thread has 0 turns!")
        
        # Check history retrieval
        history = get_history(thread_id, max_turns=20)
        if len(history) != len(thread.turns):
            print(f"  ⚠️  WARNING: get_history() returned {len(history)} turns, but thread has {len(thread.turns)}")
        
        print()
    
    print(f"{'='*80}\n")

if __name__ == "__main__":
    debug_all_threads()
```

Run with:
```bash
cd backend
source venv/bin/activate
python ../debug_context.py
```

---

## 8. Summary

This playbook provides:
- **Symptoms table** - Quick diagnosis
- **10-step debug checklist** - Systematic investigation
- **Debug tools** - Code snippets for inspection
- **Known failure modes** - Historical bugs and fixes
- **Reproduction scripts** - How to recreate issues
- **Fix prescriptions** - Step-by-step solutions

**Remember:** Most context bugs stem from:
1. Thread being overwritten instead of reused
2. History not being loaded before building context
3. Turns not being saved immediately
4. Rewriter not receiving full context

Use this playbook to diagnose and fix context issues quickly! 🔧

