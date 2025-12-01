# Context Fix Verification Guide

## Issue Confirmed ❌

**Test Result**: The context feature is **NOT working correctly**.

When testing:
1. User: "Who is Donald Trump" → ✅ Correct response
2. User: "who are his children" → ❌ Response about "John Doe" instead of "Donald Trump's children"

This confirms the provider is **NOT seeing the previous conversation turn**.

## What to Check

### 1. Backend Logs

Look for these log patterns in the backend terminal:

```
🔧 CONTEXT BUILDER: thread_id=...
Short-term history turns: X  ← Should be >= 2 for second message
```

```
📤 SENDING TO PROVIDER: perplexity/sonar-pro
Using centralized context builder ✓
Conversation history turns: X  ← Should be >= 2
```

### 2. Verify Context Builder is Being Called

The code should be calling:
```python
context_result = await context_builder.build_contextual_messages(...)
```

Check if you see `🔧 CONTEXT BUILDER` logs in the backend output.

### 3. Check Conversation History Loading

The context builder should:
1. Call `_get_recent_messages(db, thread_id)` 
2. Return messages including the "Who is Donald Trump" Q&A
3. Include them in the messages array sent to provider

### 4. Expected Messages Array (for second message)

```
[0] system: You are DAC...
[1] user: Who is Donald Trump
[2] assistant: Donald Trump is the 45th...
[3] user: Original user message:
who are his children
```

If the messages array only has 2 items (system + current user), then history is NOT being loaded.

## Potential Issues

1. **Backend not restarted**: Changes to `context_builder.py` require server restart
2. **Import error**: Context builder might not be importing correctly
3. **DB query issue**: `_get_recent_messages` might not be returning prior messages
4. **Timing issue**: Messages might not be saved to DB before second request

## How to Debug

1. **Check backend terminal output** for:
   - `🔧 CONTEXT BUILDER` logs
   - `📤 SENDING TO PROVIDER` logs
   - Any error messages

2. **Verify database**: Check if messages are being saved:
   ```sql
   SELECT * FROM messages WHERE thread_id = '<thread_id>' ORDER BY sequence;
   ```

3. **Add more logging**: In `context_builder.py`, add:
   ```python
   print(f"DEBUG: Loaded {len(short_term_history)} history messages")
   for i, msg in enumerate(short_term_history):
       print(f"  [{i}] {msg.get('role')}: {msg.get('content')[:50]}")
   ```

4. **Test with query rewriter enabled**:
   ```python
   # In config.py
   feature_corewrite: bool = True
   ```

## Next Steps

1. Restart backend server to ensure latest code is running
2. Check backend logs for context builder output
3. Verify messages are being saved to DB
4. Test again with logging enabled

