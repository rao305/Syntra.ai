# Context Invariants Specification

## 1. Overview

This document defines **non-negotiable correctness invariants** for DAC's conversation context system. These invariants govern thread storage, turn persistence, context builder behavior, API pipeline expectations, query rewriter integration, supermemory integration, and how all upstream/downstream components must handle context.

**Purpose:** Prevent regressions where follow-up questions (e.g., "who are his children" after "Who is Donald Trump") return incorrect answers because previous conversation turns were not included in the LLM prompt.

**Scope:** This specification applies to:
- Thread store implementation (`app/services/threads_store.py`)
- Context builder (`app/services/context_builder.py`)
- API endpoints (`app/api/threads.py`)
- Query rewriter (`app/services/query_rewriter.py`, `app/services/llm_context_extractor.py`)
- Supermemory integration (`app/services/memory_service.py`)
- All code that interacts with conversation history

**Critical Invariant:** Between requests in the same thread, the number of turns MUST NOT decrease unless explicitly windowed. The context builder MUST always see all previous turns before adding the current user message.

---

## 2. Global Thread Store Invariants

### 2.1 Module-Level Store

**REQUIRED:**
- A module-level dict `THREADS: Dict[str, Thread]` MUST exist in `app/services/threads_store.py`
- This dict MUST be defined at module scope, NOT inside functions or classes
- The dict MUST NOT be recreated, reinitialized, shadowed, or wrapped by functions that produce new copies

**CORRECT:**
```python
# app/services/threads_store.py
THREADS: Dict[str, Thread] = {}  # Module-level, persistent

def get_thread(thread_id: str) -> Optional[Thread]:
    return THREADS.get(thread_id)  # Direct access to module-level dict
```

**FORBIDDEN:**
```python
# BAD: Recreating dict inside function
def some_function():
    THREADS = {}  # Shadowing module-level dict
    # ...

# BAD: Wrapping in a class that recreates state
class ThreadManager:
    def __init__(self):
        self.threads = {}  # New dict per instance
```

### 2.2 Thread Object Persistence

**REQUIRED:**
- A `Thread` object contains:
  - `thread_id: str` (immutable identifier)
  - `turns: List[Turn]` (mutable list of conversation turns)
- `Thread` objects MUST persist across HTTP requests
- `Thread` objects MUST be REUSED, not replaced

**CORRECT:**
```python
def get_or_create_thread(thread_id: str) -> Thread:
    thread = THREADS.get(thread_id)
    if thread is None:
        thread = Thread(thread_id=thread_id)
        THREADS[thread_id] = thread
    return thread  # Returns SAME object on subsequent calls
```

**FORBIDDEN:**
```python
# BAD: Overwriting existing thread
def bad_function(thread_id: str):
    THREADS[thread_id] = Thread(thread_id=thread_id)  # Loses all previous turns!

# BAD: Creating new thread when one exists
def bad_function(thread_id: str):
    thread = Thread(thread_id=thread_id)  # Always creates new, ignores existing
    THREADS[thread_id] = thread
```

### 2.3 State Mutation Rules

**REQUIRED:**
- State MUST be mutated in-place through approved APIs only:
  - `add_turn(thread_id, turn)` - Appends to `thread.turns`
  - `clear_thread(thread_id)` - Explicitly clears turns (for reset actions only)
- Direct mutation of `THREADS` dict is FORBIDDEN outside `threads_store.py`

**CORRECT:**
```python
# In threads_store.py
def add_turn(thread_id: str, turn: Turn) -> None:
    thread = get_or_create_thread(thread_id)
    thread.turns.append(turn)  # In-place mutation
```

**FORBIDDEN:**
```python
# BAD: Direct mutation outside approved API
def bad_function(thread_id: str):
    THREADS[thread_id].turns = []  # Unauthorized clearing

# BAD: Replacing thread object
def bad_function(thread_id: str):
    old_thread = THREADS[thread_id]
    new_thread = Thread(thread_id=thread_id, turns=[])
    THREADS[thread_id] = new_thread  # Loses all state
```

---

## 3. Turn Persistence Invariants

### 3.1 Turn Addition Guarantees

**REQUIRED:**
- `add_turn(thread_id, turn)` MUST append exactly one turn to `thread.turns`
- It MUST NOT allocate a new `Thread` for existing `thread_id` values
- It MUST reuse the existing `Thread` object if one exists
- Turns MUST remain available for subsequent requests until explicitly windowed

**CORRECT:**
```python
def add_turn(thread_id: str, turn: Turn) -> None:
    thread = get_or_create_thread(thread_id)  # Reuses existing if present
    thread.turns.append(turn)  # Appends, does not replace
```

**FORBIDDEN:**
```python
# BAD: Creating new thread on every add_turn call
def bad_add_turn(thread_id: str, turn: Turn):
    thread = Thread(thread_id=thread_id)  # Always new
    thread.turns.append(turn)
    THREADS[thread_id] = thread  # Overwrites existing

# BAD: Replacing turns list
def bad_add_turn(thread_id: str, turn: Turn):
    thread = get_thread(thread_id)
    thread.turns = [turn]  # Replaces instead of appends
```

### 3.2 Turn Ordering Invariants

**REQUIRED:**
- Turn order MUST be preserved: `[user, assistant, user, assistant, ...]`
- Turns MUST be appended in chronological order
- The last turn in `thread.turns` MUST be the most recent conversation turn

**CORRECT:**
```python
# Request 1
add_turn(thread_id, Turn(role="user", content="Who is Donald Trump?"))
add_turn(thread_id, Turn(role="assistant", content="Donald Trump is..."))

# Request 2
add_turn(thread_id, Turn(role="user", content="who are his children"))
# Result: thread.turns = [user1, assistant1, user2]
```

**FORBIDDEN:**
```python
# BAD: Reversing order
def bad_add_turn(thread_id: str, turn: Turn):
    thread = get_thread(thread_id)
    thread.turns.insert(0, turn)  # Prepends instead of appends

# BAD: Sorting or reordering
def bad_function(thread_id: str):
    thread = get_thread(thread_id)
    thread.turns.sort(key=lambda t: t.timestamp)  # Breaks chronological order
```

### 3.3 Turn Availability Invariants

**REQUIRED:**
- Turns added via `add_turn()` MUST be immediately available to `get_history()`
- There MUST be no delay or async operation that could cause a race condition
- Turns MUST persist across HTTP requests within the same process

**CORRECT:**
```python
# Request 1: Add turns
add_turn(thread_id, Turn(role="user", content="Q1"))
add_turn(thread_id, Turn(role="assistant", content="A1"))

# Request 2: Immediately available
history = get_history(thread_id)  # Returns [Q1, A1] immediately
```

**FORBIDDEN:**
```python
# BAD: Deferred persistence
def bad_add_turn(thread_id: str, turn: Turn):
    # Save to DB, but not to in-memory store
    await save_to_db(thread_id, turn)
    # get_history() won't see this turn until DB is queried

# BAD: Async race condition
async def bad_add_turn(thread_id: str, turn: Turn):
    thread = get_thread(thread_id)
    thread.turns.append(turn)
    await asyncio.sleep(0.1)  # Race condition: get_history() might run before this completes
```

---

## 4. Context Builder Invariants

### 4.1 Core Invariant

**THE MOST CRITICAL INVARIANT:**

> **"Between requests, the number of turns MUST NOT decrease unless explicitly windowed. The context builder MUST always see all previous turns before adding the current user message."**

This means:
- If request 1 adds 2 turns (user + assistant), request 2 MUST see those 2 turns
- The context builder MUST load history BEFORE processing the current user message
- The context builder MUST use read-only functions (`get_thread`, `get_history`)

### 4.2 History Loading Order

**REQUIRED:**
- Context builder MUST load history BEFORE adding the current user message
- History loading MUST use ONLY read functions (`get_thread`, `get_history`)
- Context builder MUST NEVER create, overwrite, or clear threads

**CORRECT:**
```python
async def build_contextual_messages(thread_id: str, latest_user_message: str, ...):
    # STEP 1: Load history FIRST (read-only)
    history_turns = get_history(thread_id, max_turns=12)  # Read-only
    
    # STEP 2: Build messages array with history
    messages = []
    # ... add system prompts ...
    # ... add memory snippet ...
    for turn in history_turns:  # Previous turns
        messages.append({"role": turn.role, "content": turn.content})
    # ... add current user message ...
    
    return messages
```

**FORBIDDEN:**
```python
# BAD: Creating thread in context builder
async def bad_build_contextual_messages(thread_id: str, ...):
    thread = get_or_create_thread(thread_id)  # WRONG: Creates if missing
    # Should use get_thread() which returns None if missing

# BAD: Loading history after processing current message
async def bad_build_contextual_messages(thread_id: str, latest_user_message: str, ...):
    messages = [{"role": "user", "content": latest_user_message}]  # Current message first
    history = get_history(thread_id)  # History loaded AFTER - WRONG ORDER
    messages = history + messages  # Wrong: history should come before current
```

### 4.3 Read-Only Requirement

**REQUIRED:**
- Context builder MUST use ONLY these read-only functions:
  - `get_thread(thread_id)` - Returns `None` if thread doesn't exist (never creates)
  - `get_history(thread_id, max_turns)` - Returns `[]` if thread doesn't exist (never creates)
- Context builder MUST NEVER call:
  - `get_or_create_thread()` - This is for write paths only
  - `add_turn()` - This is for write paths only
  - Any function that mutates `THREADS` dict

**CORRECT:**
```python
def _load_short_term_history(thread_id: str) -> List[Dict[str, str]]:
    # Read-only: uses get_history, never creates
    history_turns = get_history(thread_id, max_turns=12)
    return [{"role": t.role, "content": t.content} for t in history_turns]
```

**FORBIDDEN:**
```python
# BAD: Using write functions in context builder
def bad_load_history(thread_id: str):
    thread = get_or_create_thread(thread_id)  # WRONG: Creates if missing
    return thread.turns

# BAD: Mutating thread in context builder
def bad_load_history(thread_id: str):
    thread = get_thread(thread_id)
    if thread:
        thread.turns = thread.turns[-10:]  # WRONG: Mutates thread
    return thread.turns if thread else []
```

### 4.4 Message Array Construction

**REQUIRED:**
- Context builder MUST return messages in this order:
  1. System prompts (base system prompt)
  2. Supermemory snippets (optional, if enabled)
  3. All previous turns (in chronological order)
  4. Current user message (original or rewritten)

**CORRECT:**
```python
messages = [
    {"role": "system", "content": base_system_prompt},
]

if memory_snippet:
    messages.append({"role": "system", "content": f"Long-term memory:\n{memory_snippet}"})

# Previous turns (chronological order)
for turn in history_turns:
    messages.append({"role": turn.role, "content": turn.content})

# Current user message (last)
messages.append({
    "role": "user",
    "content": rewritten_query or latest_user_message
})
```

**FORBIDDEN:**
```python
# BAD: Missing previous turns
messages = [
    {"role": "system", "content": base_system_prompt},
    {"role": "user", "content": latest_user_message}  # Missing history!
]

# BAD: Wrong order
messages = [
    {"role": "user", "content": latest_user_message},  # Current message first
    # ... history added after - WRONG ORDER
]
```

---

## 5. Sliding Window / Turn Truncation Invariants

### 5.1 Windowing Rules

**REQUIRED:**
- Windowing MUST preserve the LAST N turns (most recent)
- Windowing MUST NOT wipe the entire `turns` list unless intentionally starting a new conversation
- Windowing MUST be applied only when explicitly requested (e.g., `max_turns` parameter)

**CORRECT:**
```python
def get_history(thread_id: str, max_turns: int = 12) -> List[Turn]:
    thread = get_thread(thread_id)
    if not thread:
        return []
    
    if len(thread.turns) > max_turns:
        return list(thread.turns[-max_turns:])  # Last N turns
    return list(thread.turns)  # All turns if under limit
```

**FORBIDDEN:**
```python
# BAD: Windowing mutates the thread
def bad_get_history(thread_id: str, max_turns: int = 12):
    thread = get_thread(thread_id)
    if len(thread.turns) > max_turns:
        thread.turns = thread.turns[-max_turns:]  # WRONG: Mutates thread
    return thread.turns

# BAD: Clearing all turns
def bad_window(thread_id: str):
    thread = get_thread(thread_id)
    thread.turns = []  # WRONG: Clears all, not just old ones
```

### 5.2 Window Size Invariants

**REQUIRED:**
- Default window size MUST be at least 12 turns (6 user + 6 assistant pairs)
- Window size MUST NOT be less than 2 turns (minimum for context)
- Windowing MUST preserve at least the last complete conversation pair (user + assistant)

**CORRECT:**
```python
MAX_CONTEXT_MESSAGES = 20  # Default: 20 turns
MIN_WINDOW_SIZE = 2  # Minimum: 1 user + 1 assistant

def get_history(thread_id: str, max_turns: int = MAX_CONTEXT_MESSAGES) -> List[Turn]:
    # ... implementation ensures at least MIN_WINDOW_SIZE if turns exist
```

**FORBIDDEN:**
```python
# BAD: Window size too small
def bad_get_history(thread_id: str, max_turns: int = 1):  # Too small
    # ...

# BAD: Window that breaks conversation pairs
def bad_window(thread_id: str):
    thread = get_thread(thread_id)
    # Window might end with user message, missing assistant response
    return thread.turns[-5:]  # Might break pair structure
```

---

## 6. API Layer Invariants

### 6.1 Thread ID Consistency

**REQUIRED:**
- The API layer MUST pass the same `thread_id` across requests in the same conversation
- The API layer MUST extract `thread_id` from request headers or body and reuse it
- The API layer MUST NOT create new `thread_id` values for follow-up messages

**CORRECT:**
```python
@router.post("/{thread_id}/messages/stream")
async def add_message_streaming(
    thread_id: str,  # From URL path
    request: AddMessageRequest,
    ...
):
    # Use the thread_id from URL, don't generate new one
    context_result = await context_builder.build_contextual_messages(
        thread_id=thread_id,  # Same thread_id for follow-ups
        ...
    )
```

**FORBIDDEN:**
```python
# BAD: Generating new thread_id for each request
async def bad_add_message(request: AddMessageRequest, ...):
    thread_id = str(uuid.uuid4())  # WRONG: New ID every time
    # ...

# BAD: Ignoring thread_id from request
async def bad_add_message(request: AddMessageRequest, ...):
    thread_id = "default-thread"  # WRONG: Ignores request thread_id
    # ...
```

### 6.2 Thread Creation Rules

**REQUIRED:**
- The API layer MUST NEVER create new threads when a thread already exists
- Thread creation MUST happen only when `thread_id` is explicitly "new" or doesn't exist
- The API layer MUST check for existing threads before creating new ones

**CORRECT:**
```python
async def add_message_streaming(thread_id: str, ...):
    if thread_id == "new":
        thread_id = str(uuid.uuid4())  # Only create if explicitly "new"
    
    # Use existing thread_id for all subsequent operations
    context_result = await context_builder.build_contextual_messages(
        thread_id=thread_id,
        ...
    )
```

**FORBIDDEN:**
```python
# BAD: Always creating new thread
async def bad_add_message(thread_id: str, ...):
    new_thread_id = str(uuid.uuid4())  # WRONG: Always new
    # ...

# BAD: Not checking for existing thread
async def bad_add_message(thread_id: str, ...):
    # Always creates new thread, even if thread_id exists
    thread = Thread(id=thread_id)
    THREADS[thread_id] = thread  # Overwrites existing
```

### 6.3 Thread Store Preservation

**REQUIRED:**
- The API layer MUST NEVER clear the thread store during normal operation
- The API layer MUST preserve thread state between requests
- The API layer MUST save turns immediately (before streaming response)

**CORRECT:**
```python
async def add_message_streaming(thread_id: str, request: AddMessageRequest, ...):
    # Save user message IMMEDIATELY (before streaming)
    add_turn(thread_id, Turn(role="user", content=request.content))
    
    # Stream response
    async for chunk in stream_response():
        yield chunk
        # Collect response content
    
    # Save assistant message IMMEDIATELY (after streaming completes)
    add_turn(thread_id, Turn(role="assistant", content=response_content))
```

**FORBIDDEN:**
```python
# BAD: Clearing thread store
async def bad_add_message(thread_id: str, ...):
    THREADS.clear()  # WRONG: Clears all threads
    # ...

# BAD: Deferred persistence
async def bad_add_message(thread_id: str, ...):
    # Save to DB only, not to in-memory store
    await save_to_db(thread_id, message)
    # Next request won't see this turn in in-memory store
```

### 6.4 Logging Requirements

**REQUIRED:**
- The API layer MUST log the following for debugging:
  - `thread_id` used for each request
  - Number of turns loaded from history
  - Whether thread was found or created
  - Object identity (`id(thread)`) to verify thread reuse

**CORRECT:**
```python
async def add_message_streaming(thread_id: str, ...):
    print(f"[API] Request thread_id={thread_id!r}")
    
    context_result = await context_builder.build_contextual_messages(...)
    print(f"[API] Loaded {len(context_result.short_term_history)} history turns")
    
    thread = get_thread(thread_id)
    if thread:
        print(f"[API] Thread object id={id(thread)}, turns={len(thread.turns)}")
```

---

## 7. Query Rewriter Invariants

### 7.1 Context Input Requirements

**REQUIRED:**
- Query rewriter MUST receive the previous turns from context builder
- Query rewriter MUST receive the memory snippet (if available)
- Query rewriter MUST receive the original user message

**CORRECT:**
```python
async def build_contextual_messages(thread_id: str, latest_user_message: str, ...):
    # Load history first
    history_turns = get_history(thread_id, max_turns=12)
    
    # Load memory
    memory_snippet = await retrieve_memory(thread_id, user_id)
    
    # Pass ALL context to rewriter
    rewritten = await query_rewriter.rewrite(
        latest_user_message=latest_user_message,
        recent_history=history_turns,  # Previous turns
        memory_snippet=memory_snippet,  # Long-term memory
    )
```

**FORBIDDEN:**
```python
# BAD: Rewriter without context
async def bad_rewrite(latest_user_message: str):
    # Only receives current message, no history
    return rewrite_query(latest_user_message)  # WRONG: No context

# BAD: Rewriter with partial context
async def bad_rewrite(latest_user_message: str, history: List[Turn]):
    # Missing memory snippet
    return rewrite_query(latest_user_message, history)  # WRONG: Incomplete context
```

### 7.2 Rewriter Output Requirements

**REQUIRED:**
- Query rewriter MUST output:
  - `rewritten_query: str` - Explicit, context-aware formulation
  - Fallback to `original message` on failure
- Query rewriter MUST NOT drop or replace thread state
- Query rewriter MUST preserve the meaning of the original message

**CORRECT:**
```python
async def rewrite_query(
    latest_user_message: str,
    recent_history: List[Turn],
    memory_snippet: Optional[str] = None
) -> str:
    try:
        # LLM-based rewriting with full context
        rewritten = await llm_rewrite(latest_user_message, recent_history, memory_snippet)
        return rewritten if rewritten else latest_user_message  # Fallback
    except Exception:
        return latest_user_message  # Fallback on error
```

**FORBIDDEN:**
```python
# BAD: Rewriter that drops context
async def bad_rewrite(latest_user_message: str, history: List[Turn]):
    # Ignores history, only uses current message
    return rewrite(latest_user_message)  # WRONG: Loses context

# BAD: Rewriter that mutates thread state
async def bad_rewrite(thread_id: str, message: str):
    thread = get_thread(thread_id)
    thread.turns.clear()  # WRONG: Mutates thread
    return rewrite(message)
```

### 7.3 Non-Destructive Requirement

**REQUIRED:**
- Query rewriter MUST be non-destructive:
  - Original user message MUST always be preserved in the final prompt
  - Rewritten query is an ADDITION, not a replacement
  - If rewriter fails, original message MUST still be used

**CORRECT:**
```python
# Final message includes both original and rewritten
messages.append({
    "role": "user",
    "content": f"Original user message:\n{latest_user_message}\n\n---\n\nContextualized query:\n{rewritten_query}"
})
```

**FORBIDDEN:**
```python
# BAD: Replacing original with rewritten
messages.append({
    "role": "user",
    "content": rewritten_query  # WRONG: Original message lost
})

# BAD: Only using rewritten, no fallback
if rewritten_query:
    content = rewritten_query
else:
    content = ""  # WRONG: Empty if rewrite fails
```

---

## 8. Supermemory Integration Invariants

### 8.1 Separation of Concerns

**REQUIRED:**
- Supermemory snippet MUST NOT replace short-term history
- Supermemory MUST be inserted BEFORE turn history, not after
- Supermemory and short-term history MUST coexist in the messages array

**CORRECT:**
```python
messages = [
    {"role": "system", "content": base_system_prompt},
]

# Supermemory BEFORE history
if memory_snippet:
    messages.append({
        "role": "system",
        "content": f"Long-term memory:\n{memory_snippet}"
    })

# Short-term history AFTER supermemory
for turn in history_turns:
    messages.append({"role": turn.role, "content": turn.content})
```

**FORBIDDEN:**
```python
# BAD: Supermemory replaces history
if memory_snippet:
    messages.append({"role": "system", "content": memory_snippet})
    # Missing history_turns - WRONG

# BAD: Supermemory after history
for turn in history_turns:
    messages.append({"role": turn.role, "content": turn.content})
if memory_snippet:
    messages.append({"role": "system", "content": memory_snippet})  # WRONG ORDER
```

### 8.2 Container Tags Consistency

**REQUIRED:**
- Supermemory MUST use consistent `containerTags`:
  - `user:{userId}` for user-level memory
  - `thread:{threadId}` for thread-level memory
- Same tags MUST be used for both storage and retrieval

**CORRECT:**
```python
# Storage
await memory_service.store_memory(
    content=memory_content,
    containerTags=[f"user:{user_id}", f"thread:{thread_id}"]
)

# Retrieval
memory_context = await memory_service.retrieve_memory_context(
    containerTags=[f"user:{user_id}", f"thread:{thread_id}"]
)
```

**FORBIDDEN:**
```python
# BAD: Inconsistent tags
# Storage
await store_memory(content, tags=[f"user:{user_id}"])

# Retrieval
await retrieve_memory(tags=[f"thread:{thread_id}"])  # WRONG: Different tags

# BAD: Dynamic tag generation
tags = [f"user:{random_id()}"]  # WRONG: Tags change between calls
```

### 8.3 Memory Snippet Format

**REQUIRED:**
- Memory snippet MUST be concise (max ~2000 characters)
- Memory snippet MUST be formatted as a system message
- Memory snippet MUST NOT contain raw memory blobs (should be summarized)

**CORRECT:**
```python
if memory_context:
    # Summarize memories into concise snippet
    memory_snippet = summarize_memories(memory_context, max_chars=2000)
    messages.append({
        "role": "system",
        "content": f"Long-term memory:\n{memory_snippet}"
    })
```

**FORBIDDEN:**
```python
# BAD: Dumping raw memories
if memory_context:
    raw_memories = "\n".join([m.content for m in memory_context.memories])
    messages.append({
        "role": "system",
        "content": raw_memories  # WRONG: Too long, not summarized
    })

# BAD: Memory as user message
messages.append({
    "role": "user",  # WRONG: Should be "system"
    "content": memory_snippet
})
```

---

## 9. Testing Invariants (Regression Requirements)

### 9.1 Test Layer Requirements

**REQUIRED:**
- The following test layers MUST pass before merge:
  - **Unit tests:** `tests/test_threads_store.py` (7 tests)
  - **Integration tests:** `tests/test_context_builder_integration.py` (3 tests)
  - **E2E API tests:** `tests/test_chat_api_context.py` (2 tests)
- Total: **12 tests** MUST pass

**CORRECT:**
```bash
# All tests must pass
pytest tests/test_threads_store.py -v  # 7/7 pass
pytest tests/test_context_builder_integration.py -v  # 3/3 pass
pytest tests/test_chat_api_context.py -v  # 2/2 pass
```

**FORBIDDEN:**
```bash
# BAD: Merging with failing tests
pytest tests/test_threads_store.py -v  # 5/7 pass - WRONG: 2 failures
# Still merge - FORBIDDEN
```

### 9.2 Critical Regression Test

**REQUIRED:**
- The critical Trump regression test MUST remain intact:
  - Test: `test_build_contextual_messages_sees_previous_turns`
  - Scenario: "Who is Donald Trump" → "who are his children"
  - Assertion: Second request MUST see both previous turns
  - Assertion: Response MUST mention Trump's children, NOT John Doe/Smith

**CORRECT:**
```python
def test_build_contextual_messages_sees_previous_turns():
    # Pre-populate with first Q&A
    add_turn(thread_id, Turn(role="user", content="Who is Donald Trump?"))
    add_turn(thread_id, Turn(role="assistant", content="Donald Trump is..."))
    
    # Build context for second message
    result = await build_contextual_messages(
        thread_id=thread_id,
        latest_user_message="who are his children"
    )
    
    # MUST see previous turns
    assert len(result.short_term_history) == 2
    assert "Who is Donald Trump" in str(result.messages)
    assert "Donald Trump is" in str(result.messages)
```

**FORBIDDEN:**
```python
# BAD: Removing or disabling critical test
@pytest.mark.skip  # WRONG: Test must always run
def test_build_contextual_messages_sees_previous_turns():
    # ...

# BAD: Weakening assertions
def test_build_contextual_messages_sees_previous_turns():
    # ...
    assert len(result.short_term_history) >= 0  # WRONG: Too weak, should be == 2
```

### 9.3 Test Coverage Requirements

**REQUIRED:**
- Tests MUST cover:
  - Thread persistence across requests
  - Turn accumulation
  - Context builder seeing previous turns
  - API endpoint passing correct `thread_id`
  - Query rewriter receiving full context

**CORRECT:**
```python
# Test thread persistence
def test_thread_persistence_across_multiple_requests():
    add_turn(thread_id, Turn(...))
    add_turn(thread_id, Turn(...))
    assert len(get_history(thread_id)) == 2

# Test context builder
def test_context_builder_sees_previous_turns():
    # Pre-populate turns
    # Build context
    # Assert previous turns included
```

---

## 10. Developer Checklist

Before merging code that touches conversation context, developers MUST verify:

### 10.1 Thread Store Checklist

- [ ] Did you mutate `THREADS` directly? (FORBIDDEN - use approved APIs only)
- [ ] Did you overwrite `Thread` objects? (FORBIDDEN - reuse existing)
- [ ] Did you create new `Thread` objects when one exists? (FORBIDDEN)
- [ ] Did you clear `thread.turns` without explicit intent? (FORBIDDEN)
- [ ] Did you use `get_or_create_thread()` in read paths? (FORBIDDEN - use `get_thread()`)

### 10.2 Context Builder Checklist

- [ ] Does context builder include all previous turns? (REQUIRED)
- [ ] Does context builder load history BEFORE adding current message? (REQUIRED)
- [ ] Does context builder use read-only functions? (REQUIRED)
- [ ] Does context builder preserve turn order? (REQUIRED)
- [ ] Does context builder include memory snippet before history? (REQUIRED)

### 10.3 API Layer Checklist

- [ ] Does the API endpoint pass correct `thread_id`? (REQUIRED)
- [ ] Does the API endpoint reuse `thread_id` for follow-ups? (REQUIRED)
- [ ] Does the API endpoint save turns immediately? (REQUIRED)
- [ ] Does the API endpoint log `thread_id` and turn count? (REQUIRED)

### 10.4 Query Rewriter Checklist

- [ ] Does query rewriting preserve meaning? (REQUIRED)
- [ ] Does query rewriting receive full context (history + memory)? (REQUIRED)
- [ ] Does query rewriting fallback to original on failure? (REQUIRED)
- [ ] Does query rewriting preserve original message in prompt? (REQUIRED)

### 10.5 Testing Checklist

- [ ] Do all 12 regression tests pass? (REQUIRED)
- [ ] Does the critical Trump test pass? (REQUIRED)
- [ ] Did you add new tests for new functionality? (REQUIRED)
- [ ] Did you verify thread object identity in logs? (RECOMMENDED)

### 10.6 Logging Checklist

- [ ] Did you log `thread_id` for each request? (REQUIRED)
- [ ] Did you log number of turns loaded? (REQUIRED)
- [ ] Did you log thread object identity (`id(thread)`)? (RECOMMENDED)
- [ ] Did you log whether thread was found or created? (RECOMMENDED)

---

## 11. Anti-Corruption Layer Note (Future Improvements)

### 11.1 Current Architecture

The current implementation uses a module-level `THREADS` dict for simplicity and performance. This is acceptable for single-process deployments but has limitations:

- **Process isolation:** Threads don't persist across process restarts
- **Multi-process:** Threads don't share state across worker processes
- **Scalability:** In-memory store doesn't scale horizontally

### 11.2 Future Improvements

**Recommended (not required):**
- Move to Redis or similar distributed cache for thread storage
- Implement thread store abstraction layer to hide implementation details
- Add thread store interface that can be swapped (in-memory → Redis → DB)
- Implement thread store versioning for migration scenarios

**Important:** Any future refactoring MUST preserve all invariants defined in this specification. The abstraction layer MUST maintain the same guarantees:
- Thread persistence
- Turn accumulation
- Read/write separation
- Context builder correctness

### 11.3 Migration Strategy

If moving to Redis or another backend:
1. Implement new backend that satisfies all invariants
2. Add feature flag to switch between implementations
3. Run both implementations in parallel during migration
4. Verify all 12 tests pass with new backend
5. Remove old implementation after validation

---

## 12. Violation Consequences

### 12.1 Bug Manifestation

Violating these invariants will cause:
- **Context loss:** Follow-up questions return incorrect answers (e.g., "John Doe" instead of "Donald Trump")
- **Thread corruption:** Turns disappear between requests
- **Race conditions:** Concurrent requests see inconsistent state
- **Memory leaks:** Threads accumulate without cleanup

### 12.2 Detection

Violations can be detected by:
- Regression tests failing (especially `test_build_contextual_messages_sees_previous_turns`)
- Logs showing `turns_count=0` when it should be > 0
- Logs showing different `thread_id` values for follow-up messages
- Logs showing different `obj_id` values for the same `thread_id`

### 12.3 Remediation

If invariants are violated:
1. **Immediate:** Revert the violating change
2. **Short-term:** Add logging to identify root cause
3. **Long-term:** Add additional tests to prevent recurrence
4. **Documentation:** Update this spec if new patterns are discovered

---

## 13. Summary

This specification defines **non-negotiable correctness invariants** for DAC's conversation context system. All code that touches thread storage, turn persistence, context building, API routing, query rewriting, or memory integration MUST comply with these invariants.

**The most critical invariant:** Between requests, the number of turns MUST NOT decrease unless explicitly windowed. The context builder MUST always see all previous turns before adding the current user message.

**Enforcement:** All 12 regression tests MUST pass before merge. The critical Trump regression test MUST remain intact and passing.

**Future work:** Any refactoring MUST preserve these invariants. The abstraction layer can change, but the guarantees must remain the same.

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-16  
**Maintainer:** Backend Team  
**Review Frequency:** Quarterly or when context-related bugs are discovered

