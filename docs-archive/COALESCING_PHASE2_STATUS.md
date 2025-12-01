# Request Coalescing Phase 2 - Production Implementation Status

## ✅ Completed

### 1. Core Coalescing Infrastructure
- ✅ Created `backend/app/services/coalesce.py` - Production-grade coalescer
  - Leader/follower pattern
  - Only leader makes provider call
  - Automatic TTL-based garbage collection
  - Proper error propagation

### 2. Stream Hub for SSE Fan-out
- ✅ Created `backend/app/services/stream_hub.py` - Multi-client streaming
  - One upstream provider stream → many client streams
  - Queue-based pub/sub pattern
  - Handles slow consumers gracefully

### 3. Helper Functions
- ✅ Created `_save_turn_to_db()` helper in threads.py
  - Saves user+assistant pair atomically
  - Used only by leader
  - Handles all DB writes, audit logs, thread updates

### 4. Updated Imports
- ✅ Added imports for coalescer and stream_hub
- ✅ Removed old coalescing infrastructure imports

## 🚧 In Progress

### Non-Streaming Endpoint Refactor
**File**: `backend/app/api/threads.py`  
**Function**: `add_message()` (lines 255-556)

**Status**: Partially migrated to new coalescer

**What's Done**:
- ✅ Removed old coalescing primitives (_inflight, _message_cache, etc.)
- ✅ Added new coalesce_key generation
- ✅ Started performance tracking before coalescing

**What's Needed**:
The current function still has the old retry/provider call logic mixed in. It needs to be restructured into:

1. **Setup phase** (before coalescing):
   - Validate inputs
   - Check rate limits  
   - Build prompt
   - Generate coalesce key

2. **Leader function** (inside `coalescer.run()`):
   ```python
   async def leader_make():
       # Only leader executes this
       # 1. Acquire pacer slot
       # 2. Call provider with retries
       # 3. Save to DB using _save_turn_to_db()
       # 4. Return normalized response dict
       return response_dict, metadata
   ```

3. **Coalescer execution**:
   ```python
   response_data, meta = await coalescer.run(coal_key, leader_make)
   ```

4. **Return phase** (both leader and followers):
   ```python
   return AddMessageResponse(**response_data)
   ```

## 📋 Complete Implementation (Ready to Apply)

See `backend/app/api/threads_new_add_message.py` for the complete clean implementation.

**Key differences from current code**:
- No user_message creation before coalescing
- No DB writes before knowing if we're leader
- All leader work wrapped in `leader_make()` async function
- Followers never touch the database
- Both return identical normalized response

## 🎯 Next Steps

### Option A: Manual Integration (Recommended - Safer)
1. Review `threads_new_add_message.py` 
2. Backup current `threads.py`
3. Replace `add_message()` function (lines 255-556) with new implementation
4. Test with: `curl -X POST .../messages` (should work)
5. Run burst test: `npx autocannon ...` (should get ~100% success)

### Option B: Streaming Integration
After non-streaming works:
1. Apply similar pattern to `add_message_streaming()` (line 559+)
2. Use `stream_hub` for fan-out
3. Test with: `node sse_ttft.mjs`

## 🧪 Testing Plan

Once integrated:

```bash
# Test 1: Single request (should work as before)
curl -X POST http://localhost:8000/api/threads/<thread_id>/messages \
  -H "Content-Type: application/json" \
  -H "x-org-id: org_demo" \
  -d '{"role":"user","content":"Test","provider":"perplexity","model":"llama-3.1-sonar-small-128k-online","reason":"test","scope":"private"}'

# Test 2: Multi-thread burst (prove coalescing)
node test_coalescing.mjs
# Expect: 100% success, all share 1 provider call

# Test 3: Single-thread burst (the big test!)
npx autocannon -c 10 -a 50 -m POST --timeout 120 \
  -H "content-type: application/json" -H "x-org-id: org_demo" \
  -b '{"role":"user","content":"Test","provider":"perplexity","model":"llama-3.1-sonar-small-128k-online","reason":"test","scope":"private"}' \
  http://localhost:8000/api/threads/<FRESH_THREAD_ID>/messages
# Expect: ~100% success (not 60%)!
# Expect: Only 2 messages in thread (1 user + 1 assistant)
```

## 📊 Expected Improvements

| Metric | Before (Phase 1) | After (Phase 2) | Target |
|--------|------------------|-----------------|---------|
| Single-thread burst success | 60% (30/50) | **~100%** (49-50/50) | >95% |
| Messages created (50 reqs) | 20 (duplicates) | **2** (one pair) | <5 |
| Provider API calls (50 reqs) | 3-5 | **1** | <3 |
| Error rate | 40% | **<5%** | <10% |

## 🔧 Troubleshooting

If integration fails:
1. Check imports are correct
2. Verify `_save_turn_to_db()` function exists
3. Ensure `coalescer` and `coalesce_key` are imported
4. Check that `has_leader_writes` is in metadata dict
5. Review logs for leader vs follower execution

## 📝 Files Modified

- ✅ `backend/app/services/coalesce.py` (NEW)
- ✅ `backend/app/services/stream_hub.py` (NEW)
- 🚧 `backend/app/api/threads.py` (PARTIAL - needs completion)
- ✅ `backend/app/api/threads_new_add_message.py` (REFERENCE - complete clean implementation)

## 🎉 Success Criteria

Phase 2 is complete when:
- ✅ Single-thread burst: >95% success rate
- ✅ Only 1-2 message pairs created for 50 identical requests
- ✅ Only 1 provider API call for 50 coalesced requests
- ✅ No duplicate messages in database
- ✅ Streaming also uses fan-out (bonus)

---

**Current State**: Infrastructure ready, needs final integration into endpoints.  
**Estimated completion**: 15-30 minutes of careful refactoring.  
**Risk level**: Low (can rollback to Phase 1 implementation if needed).

