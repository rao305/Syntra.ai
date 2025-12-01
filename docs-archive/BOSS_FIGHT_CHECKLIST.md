# Boss Fight Test - Manual Checklist

Use this checklist if you prefer to test manually through the DAC UI.

## Setup

- [ ] `SUPERMEMORY_API_KEY` set in `.env.local`
- [ ] `OPENAI_API_KEY` set in `.env.local`
- [ ] Server running and ready

---

## 🔁 Phase 1: Same-session context + pronouns

**Session:** Same session throughout

### Message 1
- [ ] Send: "Who is Donald Trump?"
- [ ] ✅ Expect: Normal bio answer about Trump

### Message 2
- [ ] Send: "When was he born?"
- [ ] ✅ Check `resolved_query`: Should be "When was Donald Trump born?"
- [ ] ✅ Check answer: Should explicitly say "Donald Trump was born on June 14, 1946."
- [ ] ✅ Check: No mention of "Luis Miguel" or other random entities
- [ ] ✅ Check: Answer mentions "Donald Trump" explicitly

### Message 3
- [ ] Send: "Summarize what you just told me about him in 2 sentences."
- [ ] ✅ Check `resolved_query`: Should mention Donald Trump
- [ ] ✅ Check answer: Summary refers to Trump, not anyone else

---

## 🧠 Phase 2: Supermemory store + recall

**Session:** Continue same session

### Message 4
- [ ] Send: "My name is Alex, I study computer science at Purdue University, and I prefer dark mode and TypeScript. Please remember that."
- [ ] ✅ Check server logs: Should see `[OpenAIProvider] Tool calls made: 1`
- [ ] ✅ Check tool name: Should be `addMemory` or similar
- [ ] ✅ Check answer: Model acknowledges the request

### Message 5
- [ ] Send: "What's my name and what language do I like again?"
- [ ] ✅ Check server logs: Should see `searchMemories` tool call
- [ ] ✅ Check answer: Should say "Your name is Alex, and you like TypeScript."
- [ ] ✅ Verify: This info is NOT in recent messages (proving Supermemory worked)

---

## 🎯 Phase 3: "That university" + ranking context

**Session:** Continue same session

### Message 6
- [ ] Send: "What is Purdue University?"
- [ ] ✅ Expect: Short description of Purdue

### Message 7
- [ ] Send: "What is the computer science rank for that university?"
- [ ] ✅ Check `resolved_query`: Should be "What is the computer science rank for Purdue University?"
- [ ] ✅ Check: No "I couldn't determine which university..." confusion
- [ ] ✅ Check answer: Explicitly mentions "Purdue University"

---

## 🔄 Phase 4: Cross-session / reload test

**Action:** Start NEW session (new sessionId, same userId)

### Message 8
- [ ] **NEW SESSION**: Send "Hey, do you remember my name and what I'm studying?"
- [ ] ✅ Verify: New session history does NOT include "My name is Alex..." message
- [ ] ✅ Check server logs: Should see `searchMemories` tool call
- [ ] ✅ Check answer: Should say "Your name is Alex, and you're studying computer science at Purdue University."
- [ ] ✅ **This proves**: ContextManager works per-session, Supermemory works across sessions

---

## 🧪 Bonus: Ambiguity handling

**Session:** Continue same session (or new one)

### Message 9
- [ ] Send: "Tell me about Barack Obama and Joe Biden"
- [ ] ✅ Expect: Information about both people

### Message 10
- [ ] Send: "What year was he born?"
- [ ] ✅ Check answer: Should ask clarifying question like "Do you mean Barack Obama or Joe Biden?"
- [ ] ✅ Check: Does NOT silently guess one or the other

---

## Success Criteria

✅ **Phase 1**: All pronoun resolutions work correctly  
✅ **Phase 2**: Supermemory stores and retrieves user info  
✅ **Phase 3**: "That X" references resolve correctly  
✅ **Phase 4**: Cross-session memory retrieval works  
✅ **Bonus**: Ambiguity handled with clarifying questions  

---

## Notes

- Keep track of `sessionId` and `userId` for Phase 4
- Check server console logs for tool call messages
- Wait 2-3 seconds between storing and retrieving memory
- If any phase fails, note the specific failure point








