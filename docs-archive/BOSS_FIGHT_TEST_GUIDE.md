# Boss Fight Test Guide

Comprehensive integration test for DAC system covering:
- ContextManager (same-session context)
- EntityResolver (pronouns & "that X")
- Supermemory (add/search)
- Cross-session context

## Quick Start

```bash
cd src
npx tsx test-boss-fight.ts
```

## Prerequisites

1. **Environment Variables** (in `src/.env.local`):
   - `SUPERMEMORY_API_KEY` - Required
   - `OPENAI_API_KEY` - Required for LLM calls

2. **Dependencies**:
   ```bash
   npm install
   ```

## Test Phases

### 🔁 Phase 1: Same-session context + pronouns
- **Message 1**: "Who is Donald Trump?"
- **Message 2**: "When was he born?"
  - ✅ Checks: resolved_query should be "When was Donald Trump born?"
  - ✅ Checks: No random "Luis Miguel" nonsense
  - ✅ Checks: Answer explicitly mentions "Donald Trump was born on..."
- **Message 3**: "Summarize what you just told me about him in 2 sentences."
  - ✅ Checks: resolved_query mentions Donald Trump
  - ✅ Checks: Summary refers to Trump, not anyone else

### 🧠 Phase 2: Supermemory store + recall
- **Message 4**: "My name is Alex, I study computer science at Purdue University, and I prefer dark mode and TypeScript. Please remember that."
  - ✅ Checks: `addMemory` tool call detected
  - ✅ Checks: Memory content includes Alex, CS at Purdue, dark mode, TypeScript
- **Message 5**: "What's my name and what language do I like again?"
  - ✅ Checks: `searchMemories` tool call detected
  - ✅ Checks: Answer mentions "Alex" and "TypeScript"
  - ✅ Checks: Info NOT in recent messages (proving Supermemory worked)

### 🎯 Phase 3: "That university" + ranking context
- **Message 6**: "What is Purdue University?"
  - ✅ Checks: Short description provided
- **Message 7**: "What is the computer science rank for that university?"
  - ✅ Checks: resolved_query should be "What is the computer science rank for Purdue University?"
  - ✅ Checks: No "I couldn't determine which university..." confusion
  - ✅ Checks: Answer explicitly mentions Purdue University

### 🔄 Phase 4: Cross-session / reload test
- **Message 8**: "Hey, do you remember my name and what I'm studying?"
  - ✅ Checks: New session has clean history (no old messages)
  - ✅ Checks: `searchMemories` tool call detected
  - ✅ Checks: Answer mentions "Alex" and "computer science at Purdue University"
  - ✅ **This proves**: ContextManager works per-session, Supermemory works across sessions

### 🧪 Bonus: Ambiguity handling
- **Message 9**: "Tell me about Barack Obama and Joe Biden"
- **Message 10**: "What year was he born?"
  - ✅ Checks: Model asks clarifying question (e.g., "Do you mean Barack Obama or Joe Biden?")
  - ✅ Checks: Does NOT silently guess

## Expected Output

The test script will:
1. Run all 10 messages in sequence
2. Check each phase's requirements
3. Display detailed results for each message
4. Show a summary at the end

### Success Output
```
🎉 ALL TESTS PASSED! Boss fight complete! 🎉
```

### Failure Output
```
⚠️  X test(s) failed. Review errors above.
```

## Manual Testing (Alternative)

If you prefer to test manually through the UI:

1. **Phase 1**: Send messages 1-3 in order
   - Check resolved_query in response
   - Verify entity resolution

2. **Phase 2**: Send messages 4-5
   - Check server logs for tool calls
   - Verify memory storage and retrieval

3. **Phase 3**: Send messages 6-7
   - Check "that university" resolution

4. **Phase 4**: Start new session (new sessionId, same userId)
   - Send message 8
   - Verify cross-session memory retrieval

5. **Bonus**: Send messages 9-10
   - Verify ambiguity handling

## Troubleshooting

### "Supermemory is not available"
- Check `SUPERMEMORY_API_KEY` is set in `.env.local`
- Restart after adding the key

### "OpenAI API key is not configured"
- Check `OPENAI_API_KEY` is set in `.env.local`

### Tool calls not detected
- Check server logs for `[OpenAIProvider] Tool calls made:`
- Verify model supports tool calling (GPT-4, GPT-4o, etc.)

### Memory not persisting across sessions
- Verify `userId` is the same across sessions
- Check `sessionId` is different for new session
- Wait a few seconds between storing and retrieving

## What This Test Proves

✅ **ContextManager** - Maintains conversation history per session  
✅ **EntityResolver** - Resolves pronouns and vague references correctly  
✅ **Supermemory** - Stores and retrieves information across sessions  
✅ **Cross-session memory** - Works with same userId, different sessionId  
✅ **Ambiguity handling** - Asks for clarification when multiple entities exist  

## Next Steps

After passing the boss fight test:
1. ✅ Integration is complete and working
2. ✅ Ready for production use
3. ✅ Consider adding more edge cases
4. ✅ Monitor tool call usage in production








