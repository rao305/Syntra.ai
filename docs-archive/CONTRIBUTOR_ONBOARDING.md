# Contributor Onboarding Guide - Conversation Context System

## 1. Purpose

### What This System Does

The conversation context system ensures that follow-up questions in a chat conversation correctly reference previous messages. For example:

- **User:** "Who is Donald Trump?"
- **Assistant:** "Donald Trump is the 45th president..."
- **User:** "who are his children"
- **Assistant:** "Donald Trump has five children: Donald Jr., Ivanka, Eric, Tiffany, and Barron."

The system maintains **short-term conversation history** (recent turns) and **long-term memory** (supermemory) to provide rich context to LLM providers.

### Why Context Correctness is Mission-Critical

Without proper context:
- Follow-up questions fail (e.g., "who are his children" returns answers about random people)
- Pronouns can't be resolved ("his" doesn't refer to the right entity)
- Conversations feel broken and disconnected
- User experience degrades significantly

### Historical Failure Case: The Trump/John Doe Bug

**The Bug:**
1. User asks: "Who is Donald Trump?"
2. Assistant responds correctly about Trump
3. User asks: "who are his children"
4. Assistant responds about "John Doe" or "John Smith" instead of Trump's children

**Root Cause:**
- The context builder was not seeing previous conversation turns
- The thread store was being overwritten or cleared between requests
- The second request had 0 turns in history instead of 2

**Impact:**
- Complete breakdown of conversation continuity
- Users received incorrect answers
- System appeared broken

**Fix:**
- Implemented strict read/write separation in thread store
- Added comprehensive regression tests
- Created invariant specifications

**Lesson:** Context correctness is not optional—it's the foundation of a working conversational AI system.

---

## 2. System Overview (High Level)

### Core Components

#### Threads
- A **thread** represents a single conversation session
- Each thread has a unique `thread_id` (UUID string)
- Threads persist conversation turns in memory (and optionally in database)

#### Turns
- A **turn** is a single message in a conversation
- Each turn has:
  - `role`: "user" or "assistant"
  - `content`: The message text
- Turns are stored in chronological order: `[user1, assistant1, user2, assistant2, ...]`

#### Context Builder
- **Purpose:** Builds the complete `messages` array sent to LLM providers
- **Input:** `thread_id`, `latest_user_message`, `user_id`, `org_id`
- **Output:** `messages` array with:
  1. System prompts
  2. Supermemory snippets (optional)
  3. Previous conversation turns
  4. Current user message (original or rewritten)

#### Query Rewriter
- **Purpose:** Makes user messages explicit and context-aware
- **Example:** "who are his children" → "Who are Donald Trump's children?"
- **Input:** Latest message + conversation history + memory snippet
- **Output:** Rewritten query that resolves pronouns and references

#### Supermemory
- **Purpose:** Long-term memory across conversation sessions
- **Storage:** Memories stored with `containerTags` (e.g., `user:{userId}`, `thread:{threadId}`)
- **Retrieval:** Relevant memories retrieved and injected as system messages
- **Separation:** Supermemory supplements, never replaces, short-term history

#### Router / Providers
- **Purpose:** Selects the appropriate LLM provider/model for each request
- **Input:** Query, conversation history, metadata
- **Output:** Provider selection (e.g., Perplexity Sonar, OpenAI GPT-4)
- **Note:** Router does NOT affect context—all providers receive the same rich context

#### API Entrypoints
- **Streaming:** `POST /api/threads/{thread_id}/messages/stream`
- **Non-streaming:** `POST /api/threads/{thread_id}/messages`
- **Both:** Use the same context builder and thread store

---

## 3. How Message Flow Works (Step-by-Step)

### Request 1: First Message in a Conversation

```
1. User sends: "Who is Donald Trump?"
   └─> API receives request with thread_id="new" or existing UUID

2. API creates or retrieves thread
   └─> thread_id = "abc-123-def-456"
   └─> THREADS["abc-123-def-456"] = Thread(thread_id="abc-123-def-456", turns=[])

3. Context builder runs
   └─> get_history(thread_id) → returns [] (no previous turns)
   └─> retrieve_memory(thread_id, user_id) → returns None (no memory yet)
   └─> rewrite_query("Who is Donald Trump?", history=[], memory=None)
   └─> Returns: messages = [
         {role: "system", content: "You are DAC..."},
         {role: "user", content: "Who is Donald Trump?"}
       ]

4. Router selects provider
   └─> intelligent_router.route(...) → Perplexity Sonar

5. Provider responds
   └─> Streams: "Donald Trump is the 45th president..."

6. Turns saved IMMEDIATELY
   └─> add_turn(thread_id, Turn(role="user", content="Who is Donald Trump?"))
   └─> add_turn(thread_id, Turn(role="assistant", content="Donald Trump is..."))
   └─> THREADS["abc-123-def-456"].turns = [user_turn, assistant_turn]
```

### Request 2: Follow-up Message (Same Thread)

```
1. User sends: "who are his children"
   └─> API receives request with thread_id="abc-123-def-456" (SAME thread)

2. API retrieves existing thread
   └─> get_thread("abc-123-def-456") → returns existing Thread object
   └─> Thread has 2 turns already

3. Context builder runs (CRITICAL STEP)
   └─> get_history(thread_id) → returns [user_turn, assistant_turn] (2 turns!)
   └─> retrieve_memory(thread_id, user_id) → returns None (still no memory)
   └─> rewrite_query("who are his children", history=[user_turn, assistant_turn], memory=None)
   └─> Returns: "Who are Donald Trump's children?" (rewritten with context!)
   └─> Returns: messages = [
         {role: "system", content: "You are DAC..."},
         {role: "user", content: "Who is Donald Trump?"},        ← Previous turn
         {role: "assistant", content: "Donald Trump is..."},      ← Previous turn
         {role: "user", content: "Who are Donald Trump's children?"}  ← Current (rewritten)
       ]

4. Router selects provider
   └─> intelligent_router.route(...) → Perplexity Sonar

5. Provider responds (with full context!)
   └─> Streams: "Donald Trump has five children: Donald Jr., Ivanka, Eric, Tiffany, and Barron."

6. Turns saved IMMEDIATELY
   └─> add_turn(thread_id, Turn(role="user", content="who are his children"))
   └─> add_turn(thread_id, Turn(role="assistant", content="Donald Trump has five children..."))
   └─> THREADS["abc-123-def-456"].turns = [user1, assistant1, user2, assistant2] (4 turns)
```

### Key Points

- **Thread ID must be consistent** across requests in the same conversation
- **Context builder must run BEFORE saving the current user message**
- **Turns must be saved IMMEDIATELY** (not deferred) so they're available for the next request
- **History must include ALL previous turns** (not just the last one)

---

## 4. Core Rules New Devs Must Know

### Thread Store Rules

1. **Never overwrite THREADS**
   - ❌ `THREADS = {}` inside a function
   - ✅ Use module-level `THREADS` dict

2. **Never clear `.turns`**
   - ❌ `thread.turns = []`
   - ✅ Only use `clear_thread()` for explicit reset actions

3. **Never mutate threads in read paths**
   - ❌ `get_thread()` creating new threads
   - ✅ `get_thread()` returns `None` if thread doesn't exist

4. **Always reuse Thread objects**
   - ❌ `THREADS[thread_id] = Thread(...)` when thread exists
   - ✅ `get_or_create_thread()` reuses existing threads

### API Rules

5. **Always reuse the same thread_id**
   - ❌ Generating new `thread_id` for each request
   - ✅ Pass `thread_id` from request and reuse it

6. **API must pass through correct parameters**
   - ❌ Missing `thread_id` in context builder call
   - ✅ Pass `thread_id`, `user_id`, `org_id` correctly

### Query Rewriter Rules

7. **Rewriter must be non-destructive**
   - ❌ Replacing original message with rewritten version
   - ✅ Include both original and rewritten in final prompt

8. **Rewriter must receive full context**
   - ❌ Rewriter only seeing current message
   - ✅ Rewriter receives history + memory + current message

### Supermemory Rules

9. **Supermemory must never replace short-term context**
   - ❌ Using memory snippet instead of history
   - ✅ Memory snippet supplements history (both included)

10. **Supermemory must use consistent containerTags**
    - ❌ Different tags for storage vs retrieval
    - ✅ Same tags: `user:{userId}`, `thread:{threadId}`

---

## 5. Testing Requirements

### All Tests Must Pass

Before merging any code that touches conversation context:

```bash
# Run all context-related tests
pytest tests/test_threads_store.py tests/test_context_builder_integration.py tests/test_chat_api_context.py -v

# Expected: 12 tests pass
# - 7 thread store tests
# - 3 context builder integration tests
# - 2 E2E API tests
```

### Critical Regression Test

The test `test_build_contextual_messages_sees_previous_turns` MUST always pass:

```bash
# Run critical test
pytest tests/test_context_builder_integration.py::test_build_contextual_messages_sees_previous_turns -v
```

**This test simulates:**
- First message: "Who is Donald Trump?"
- Second message: "who are his children"
- Assertion: Context builder sees both previous turns

### Running Tests Locally

```bash
# Activate virtual environment
cd backend
source venv/bin/activate

# Run all tests
pytest -v

# Run specific test file
pytest tests/test_threads_store.py -v

# Run with verbose output
pytest -v -s

# Run with coverage
pytest --cov=app.services.threads_store --cov=app.services.context_builder
```

### CI Requirements

- All 12 tests must pass in CI before merge
- Critical regression test must pass
- No test should be skipped or disabled

---

## 6. Code Navigation Map

### Thread Store
- **Location:** `backend/app/services/threads_store.py`
- **Key Functions:**
  - `get_thread(thread_id)` - Read-only lookup
  - `get_or_create_thread(thread_id)` - Safe create
  - `add_turn(thread_id, turn)` - Add turn
  - `get_history(thread_id, max_turns)` - Get history
- **Global:** `THREADS: Dict[str, Thread]` - Module-level store

### Context Builder
- **Location:** `backend/app/services/context_builder.py`
- **Key Class:** `ContextBuilder`
- **Key Method:** `build_contextual_messages(...)`
- **Dependencies:** `threads_store`, `memory_service`, `query_rewriter`

### API Endpoints
- **Location:** `backend/app/api/threads.py`
- **Key Endpoints:**
  - `POST /api/threads/{thread_id}/messages/stream` - Streaming
  - `POST /api/threads/{thread_id}/messages` - Non-streaming
- **Key Functions:**
  - `add_message_streaming()` - Streaming handler
  - `add_message()` - Non-streaming handler

### Query Rewriter
- **Location:** 
  - `backend/app/services/query_rewriter.py` - Rule-based
  - `backend/app/services/llm_context_extractor.py` - LLM-based
- **Key Functions:**
  - `rewrite()` - Rule-based rewriting
  - `resolve_references_in_query()` - LLM-based rewriting

### Router Logic
- **Location:** `backend/app/services/intelligent_router.py`
- **Key Function:** `route(...)`
- **Note:** Router selects provider, but doesn't affect context

### Tests
- **Location:** `backend/tests/`
- **Files:**
  - `test_threads_store.py` - Thread store unit tests
  - `test_context_builder_integration.py` - Context builder integration tests
  - `test_chat_api_context.py` - E2E API tests

---

## 7. Common Mistakes to Avoid

### Mistake 1: Recreating THREADS

```python
# ❌ WRONG: Recreating dict inside function
def some_function():
    THREADS = {}  # Shadows module-level dict
    # ...

# ✅ CORRECT: Use module-level dict
from app.services.threads_store import THREADS
# THREADS is already defined at module level
```

### Mistake 2: Returning New Thread Objects

```python
# ❌ WRONG: Always creating new Thread
def bad_get_thread(thread_id: str):
    return Thread(thread_id=thread_id)  # New object every time

# ✅ CORRECT: Reuse existing Thread
def get_thread(thread_id: str):
    return THREADS.get(thread_id)  # Returns existing or None
```

### Mistake 3: Forgetting to Pass thread_id

```python
# ❌ WRONG: Missing thread_id
async def bad_build_context():
    result = await context_builder.build_contextual_messages(
        latest_user_message="Hello"
        # Missing thread_id!
    )

# ✅ CORRECT: Always pass thread_id
async def build_context(thread_id: str):
    result = await context_builder.build_contextual_messages(
        thread_id=thread_id,
        latest_user_message="Hello"
    )
```

### Mistake 4: Clearing Turns Accidentally

```python
# ❌ WRONG: Clearing turns in normal flow
def bad_function(thread_id: str):
    thread = get_thread(thread_id)
    thread.turns = []  # Loses all history!

# ✅ CORRECT: Only clear for explicit reset
def reset_conversation(thread_id: str):
    clear_thread(thread_id)  # Explicit reset action
```

### Mistake 5: Incorrect Async Handling

```python
# ❌ WRONG: Deferred persistence
async def bad_add_turn(thread_id: str, turn: Turn):
    await save_to_db(thread_id, turn)
    # Not saved to in-memory store - next request won't see it!

# ✅ CORRECT: Immediate persistence
def add_turn(thread_id: str, turn: Turn):
    thread = get_or_create_thread(thread_id)
    thread.turns.append(turn)  # Immediate, synchronous
```

### Mistake 6: Rewriter Returning Wrong Type

```python
# ❌ WRONG: Rewriter returning string when dict expected
def bad_rewrite(message: str):
    return "rewritten message"  # String, but caller expects dict

# ✅ CORRECT: Rewriter returns expected type
def rewrite(message: str) -> str:
    return "rewritten message"  # String is correct
```

### Mistake 7: Rewriter Failing Open

```python
# ❌ WRONG: Rewriter fails silently
def bad_rewrite(message: str):
    try:
        return rewrite_with_llm(message)
    except:
        return ""  # Empty string - loses original message!

# ✅ CORRECT: Rewriter falls back to original
def rewrite(message: str) -> str:
    try:
        return rewrite_with_llm(message)
    except:
        return message  # Fallback to original
```

---

## 8. Quick Start Checklist for New Devs

Before contributing code that touches conversation context, verify:

### Pre-Development

- [ ] Read `CONTEXT_INVARIANTS_SPEC.md` completely
- [ ] Understand the difference between read and write paths
- [ ] Know where `threads_store.py`, `context_builder.py`, and API endpoints live
- [ ] Understand the message flow (Request 1 → Request 2)

### During Development

- [ ] Using `get_thread()` in read paths (not `get_or_create_thread()`)
- [ ] Using `get_or_create_thread()` in write paths (not `get_thread()`)
- [ ] Passing `thread_id` consistently across function calls
- [ ] Saving turns immediately (not deferred)
- [ ] Including all previous turns in context builder output
- [ ] Not mutating `THREADS` dict directly
- [ ] Not clearing `thread.turns` accidentally

### Pre-Merge

- [ ] All 12 regression tests pass locally
- [ ] Critical regression test (`test_build_contextual_messages_sees_previous_turns`) passes
- [ ] Logs show correct `thread_id` continuity
- [ ] Logs show correct turn counts (`short_term_history_len >= expected`)
- [ ] Logs show thread object identity is consistent (`obj_id` same across requests)
- [ ] Code review includes context system expert
- [ ] No forbidden patterns from Section 7

### Post-Merge

- [ ] Monitor logs for context-related errors
- [ ] Verify tests pass in CI
- [ ] Check that follow-up questions work correctly in staging

---

## 9. Getting Help

### Resources

- **Invariants Spec:** `CONTEXT_INVARIANTS_SPEC.md` - Complete technical specification
- **Debugging Playbook:** `CONTEXT_DEBUGGING_PLAYBOOK.md` - How to diagnose issues
- **Architecture Diagram:** `MEMORY_PIPELINE_ARCHITECTURE.md` - Visual system overview
- **Test Suite:** `tests/test_threads_store.py`, `tests/test_context_builder_integration.py`, `tests/test_chat_api_context.py`

### When to Ask for Help

- If you're unsure whether your code violates an invariant
- If tests are failing and you can't figure out why
- If you see unexpected behavior in logs (e.g., `turns_count=0` when it should be > 0)
- If you need to refactor thread store or context builder

### Code Review Checklist

When reviewing code that touches context:

1. Does it follow read/write separation?
2. Does it preserve thread persistence?
3. Does it include all previous turns?
4. Does it pass all 12 tests?
5. Does it maintain backward compatibility?

---

## 10. Summary

The conversation context system is the foundation of DAC's conversational AI. It must work correctly for every request, every time.

**Remember:**
- Context correctness is mission-critical
- Follow the invariants strictly
- Run all tests before merging
- When in doubt, ask for help

**The most important rule:** Between requests, the number of turns MUST NOT decrease unless explicitly windowed. The context builder MUST always see all previous turns before adding the current user message.

Welcome to the team! 🎉

