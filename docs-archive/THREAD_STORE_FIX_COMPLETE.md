# Thread Store Fix - Complete Implementation

## Summary

Implemented the canonical thread store API with strict read/write separation to fix the bug where context builder was finding 0 turns when it should find previous turns.

## Changes Made

### 1. Created `backend/app/services/threads_store.py`

**New safe API:**
- `get_thread(thread_id)` - Pure lookup, NEVER creates or overwrites (read-only)
- `get_or_create_thread(thread_id)` - Safe create, only creates if missing (write path)
- `add_turn(thread_id, turn)` - Adds turn, uses get_or_create_thread (write path)
- `get_history(thread_id, max_turns)` - Gets history, uses get_thread (read-only)
- `clear_thread(thread_id)` - Explicit clear (for reset actions only)

**Key invariants:**
- Only `get_or_create_thread` and `add_turn` can create new Thread objects
- `get_thread` and `get_history` NEVER mutate THREADS dict
- No other code should directly access `THREADS[thread_id] = Thread(...)`

### 2. Updated `backend/app/services/context_builder.py`

**Changed:**
- `_load_short_term_history()` now uses `get_history()` from `threads_store` (read-only)
- Removed direct calls to `get_thread()` that could create threads
- Added logging: `Conversation history turns: {len} (before adding current user message)`

**Result:** Context builder is now READ-ONLY on threads - it never creates or overwrites them.

### 3. Updated `backend/app/api/threads.py`

**Changed:**
- `add_turn()` calls now use `threads_store.add_turn()` (write path)
- Background cleanup now uses `threads_store.get_thread()` and `threads_store.add_turn()` (safe sync)
- Removed imports of `add_turn` and `Turn` from `memory_manager`
- Updated non-streaming path to use `threads_store.get_history()` for context

**Result:** All write operations use the safe `get_or_create_thread` path.

### 4. Logging Enhancements

**Added object identity logging:**
- `obj_id={id(thread)}` in all thread store operations
- This allows us to verify we're getting the same Thread object across requests

## Testing

### Expected Behavior After Fix:

1. **First Request:**
   - `add_turn BEFORE: obj_id=..., len(turns)=0`
   - `add_turn AFTER: obj_id=..., len(turns)=1` (user)
   - `add_turn AFTER: obj_id=..., len(turns)=2` (assistant)

2. **Second Request (BEFORE saving new user message):**
   - `get_history: obj_id=..., len(turns)=2` (same obj_id as request 1)
   - `short_term_history_len=2`
   - `Conversation history turns: 2 (before adding current user message)`

3. **Result:**
   - Second answer should be about **Donald Trump's children**, not John Doe

## Next Steps

1. Restart backend
2. Run Trump test:
   - First: "Who is Donald Trump"
   - Second: "who are his children"
3. Verify logs show:
   - Same `obj_id` across requests
   - `turns_count=2` on second request
   - Correct answer about Trump's children

## Files Modified

- ✅ `backend/app/services/threads_store.py` (NEW)
- ✅ `backend/app/services/context_builder.py`
- ✅ `backend/app/api/threads.py`

## Files Still Using `memory_manager`

These files still import from `memory_manager` but for non-thread-store operations:
- `backend/app/services/route_and_call.py` - uses `build_prompt_for_model`, `smooth_intent`, `update_last_intent`
- `backend/app/api/router.py` - uses `smooth_intent`, `update_last_intent`

These are fine - they're not doing thread store operations, just using other memory_manager utilities.

