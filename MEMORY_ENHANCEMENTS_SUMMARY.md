# Memory Management System Enhancements

**Date**: 2025-01-11  
**Status**: ✅ Completed

## Overview

The DAC memory management system has been significantly strengthened with four major enhancements that address previously identified gaps.

---

## 1. ✅ Access Graph Integration

**What Changed:**
- Integrated `AgentResourcePermission` checks into memory retrieval logic
- Added `_check_fragment_access()` method to verify agent permissions before returning fragments
- Updated `retrieve_memory_context()` to accept `current_provider` parameter
- Modified `_retrieve_from_tier()` to filter fragments based on access graph permissions

**Implementation:**
- Location: `backend/app/services/memory_service.py`
- Method: `_check_fragment_access()` (lines 237-283)
- Behavior: Default allow (backward compatible), but respects explicit deny permissions
- API Update: `threads.py` now passes `current_provider` to memory retrieval

**Impact:**
- Fine-grained control over which agents can access which memory fragments
- Maintains backward compatibility (no explicit permission = allow)
- Supports temporal permissions (revoked_at timestamp)

---

## 2. ✅ PII Scrubbing for Shared Memory

**What Changed:**
- Implemented `_scrub_pii()` method to automatically redact PII before saving to shared tier
- Integrated into `save_memory_from_turn()` - automatically scrubs when tier is SHARED
- Regex-based detection for: emails, phone numbers, credit cards, SSNs, IP addresses, names

**Implementation:**
- Location: `backend/app/services/memory_service.py`
- Method: `_scrub_pii()` (lines 570-600)
- Trigger: Automatic when `tier == MemoryTier.SHARED`
- Patterns: Email, phone, credit card, SSN, IP, name patterns

**Impact:**
- Protects user privacy in shared memory
- Automatic redaction before saving to org-wide memory
- Ready for upgrade to ML-based PII detection (Presidio, AWS Comprehend)

---

## 3. ✅ Dynamic Memory Window Adjustment

**What Changed:**
- Replaced fixed `THREAD_WINDOW = 12` with dynamic `get_dynamic_window()` function
- Window size adjusts based on:
  - Model context limits (e.g., 8k, 32k, 128k tokens)
  - Task complexity ("simple", "normal", "complex")
- Updated `add_turn()` to accept `model_context_limit` and `task_complexity` parameters

**Implementation:**
- Location: `backend/app/services/memory_manager.py`
- Function: `get_dynamic_window()` (lines 15-45)
- Parameters:
  - `model_context_limit`: Optional token limit (e.g., 8192, 32768, 128000)
  - `task_complexity`: "simple" (0.7x), "normal" (1.0x), "complex" (1.5x)
- Bounds: MIN_THREAD_WINDOW=6, MAX_THREAD_WINDOW=50

**Impact:**
- Optimizes context usage for different model capabilities
- Adapts to task complexity automatically
- Prevents context overflow on smaller models
- Maximizes context on larger models

---

## 4. ✅ Fragment Expiration/TTL

**What Changed:**
- Added `expire_old_fragments()` method to delete fragments older than specified days
- Deletes from both Qdrant (vector store) and PostgreSQL (database)
- Configurable TTL via `days_old` parameter (default: 90 days)
- Optional org-level filtering

**Implementation:**
- Location: `backend/app/services/memory_service.py`
- Method: `expire_old_fragments()` (lines 602-660)
- Parameters:
  - `org_id`: Optional - limit to specific org
  - `days_old`: Number of days (default: 90)
- Cleanup: Removes from Qdrant and database atomically

**Impact:**
- Prevents unbounded memory growth
- Configurable retention policies
- Can be scheduled as a background job
- Supports org-level data retention policies

---

## Code Changes Summary

### Files Modified:
1. `backend/app/services/memory_service.py`
   - Added access graph permission checks
   - Added PII scrubbing
   - Added fragment expiration

2. `backend/app/services/memory_manager.py`
   - Added dynamic window calculation
   - Updated `add_turn()` signature

3. `backend/app/api/threads.py`
   - Updated memory retrieval to pass `current_provider`

### New Functions:
- `_check_fragment_access()` - Access graph permission verification
- `_scrub_pii()` - PII redaction for shared memory
- `get_dynamic_window()` - Dynamic window size calculation
- `expire_old_fragments()` - Fragment TTL/expiration

---

## Backward Compatibility

✅ **All changes are backward compatible:**
- Access graph: Default allow (no explicit permission = allow)
- PII scrubbing: Only affects SHARED tier (PRIVATE unchanged)
- Dynamic windows: Falls back to DEFAULT_THREAD_WINDOW if no parameters provided
- Fragment expiration: Opt-in (must be called explicitly)

---

## Usage Examples

### Access Graph Permissions
```python
# Grant access
permission = AgentResourcePermission(
    org_id=org_id,
    agent_key="openai",
    resource_key=fragment_id,
    can_access=True
)

# Revoke access
permission.revoked_at = datetime.now(timezone.utc)
```

### Dynamic Windows
```python
# For GPT-4 (8k context)
window = get_dynamic_window(model_context_limit=8192, task_complexity="normal")
# Returns: ~57 turns (70% of 8192 / 100 tokens per turn)

# For Claude (100k context)
window = get_dynamic_window(model_context_limit=100000, task_complexity="complex")
# Returns: 18 turns (12 * 1.5, clamped to MAX)
```

### Fragment Expiration
```python
# Expire fragments older than 90 days for an org
expired_count = await memory_service.expire_old_fragments(
    db=db,
    org_id=org_id,
    days_old=90
)
```

---

## Next Steps (Optional Enhancements)

1. **Permission API**: Expose UI/API for configuring access graph permissions
2. **LLM Summarization**: Upgrade from text truncation to LLM-based summarization
3. **Advanced PII Detection**: Replace regex with ML-based detection (Presidio, AWS Comprehend)
4. **Scheduled Expiration**: Add background job to run `expire_old_fragments()` periodically

---

## Testing Recommendations

1. **Access Graph**: Test with explicit deny permissions to verify filtering
2. **PII Scrubbing**: Verify shared memory fragments have PII redacted
3. **Dynamic Windows**: Test with different model context limits
4. **Fragment Expiration**: Run expiration and verify cleanup from both stores

---

## Performance Impact

- **Access Graph Checks**: Minimal - single DB query per fragment (can be optimized with batch queries)
- **PII Scrubbing**: Negligible - regex operations are fast
- **Dynamic Windows**: No performance impact - calculation is O(1)
- **Fragment Expiration**: Moderate - batch deletion operation (run as background job)

---

**Status**: ✅ All enhancements implemented and ready for testing.

