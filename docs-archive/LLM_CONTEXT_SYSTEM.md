# LLM-Based Context System - No Hardcoding! 🧠

## Overview

**NEW APPROACH**: Uses LLM (Gemini Flash) to understand context dynamically.
**NO hardcoded patterns** - works for ANY topic: people, places, books, concepts, etc.

## How It Works

### Before (Hardcoded Regex Patterns) ❌
```python
# Limited to predefined patterns
university_patterns = ["University of", "MIT", "Stanford"]
company_patterns = ["OpenAI", "Google", "Microsoft"]
# What about: person names? book titles? concepts? locations?
```

### After (LLM-Based) ✅
```python
# LLM extracts ANY entity from conversation
entities = extract_context_with_llm(conversation)
# Returns: people, places, products, concepts, dates, etc.
# No patterns needed!
```

## Architecture

```
User: "Tell me about Einstein"
       ↓
[LLM Context Extractor]
   Analyzes conversation → Extracts: {name: "Albert Einstein", type: "person"}
       ↓
User: "What did he discover?"
       ↓
[LLM Query Rewriter]
   Detects "he" → Looks at entities → Resolves to "Albert Einstein"
   Rewrites: "What did Albert Einstein discover?"
       ↓
[Provider] Gets context-aware query ✅
```

## Key Features

### 1. Universal Entity Extraction
Works for ANY topic:
- ✅ People: "Einstein", "Marie Curie", "Steve Jobs"
- ✅ Places: "Paris", "Stanford campus", "Tokyo"
- ✅ Products: "iPhone", "ChatGPT", "Tesla Model 3"
- ✅ Concepts: "Relativity", "Machine Learning", "Democracy"
- ✅ Books: "1984", "The Great Gatsby"
- ✅ Dates/Events: "World War II", "1969 moon landing"

### 2. Intelligent Pronoun Resolution
Handles ANY pronoun:
- ✅ "it", "that", "this", "they", "them"
- ✅ "he", "she", "his", "her"
- ✅ "that book", "this person", "that company"
- ✅ Context-dependent resolution

### 3. Ambiguity Detection
LLM decides when to ask for clarification:
```
User: "Tell me about Apple and Microsoft"
User: "What did it invent?"
LLM: "Ambiguous! Which one: Apple or Microsoft?"
```

## Implementation

### Entity Extraction (`llm_context_extractor.py`)

```python
async def extract_context_with_llm(
    conversation_history: List[Dict[str, str]],
    max_entities: int = 10
) -> List[Dict[str, Any]]:
    """
    LLM analyzes conversation and extracts important entities.

    Returns:
        [
          {"name": "Albert Einstein", "type": "person", "context": "..."},
          {"name": "Theory of Relativity", "type": "concept", "context": "..."}
        ]
    """
```

**Prompt to LLM:**
```
Analyze this conversation and extract important entities.
Return JSON with: name, type, context
```

**Example Output:**
```json
[
  {
    "name": "Albert Einstein",
    "type": "person",
    "context": "Physicist being discussed"
  },
  {
    "name": "Theory of Relativity",
    "type": "concept",
    "context": "Scientific theory mentioned"
  }
]
```

### Query Rewriting (`llm_context_extractor.py`)

```python
async def rewrite_query_with_llm(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    entities: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    LLM rewrites user query to be self-contained.

    Returns:
        {
          "rewritten": "self-contained query",
          "needs_clarification": false,
          "reasoning": "why it was rewritten"
        }
    """
```

**Prompt to LLM:**
```
Recent conversation:
user: Tell me about Albert Einstein
assistant: Einstein was a physicist...

Entities mentioned:
- Albert Einstein (person): Physicist being discussed
- Theory of Relativity (concept): Scientific theory

User's latest message: "What did he discover?"

Rewrite to be self-contained.
```

**Example Output:**
```json
{
  "rewritten": "What did Albert Einstein discover?",
  "needs_clarification": false,
  "reasoning": "Replaced 'he' with 'Albert Einstein' from context"
}
```

## Advantages Over Hardcoded Patterns

| Feature | Hardcoded Regex | LLM-Based |
|---------|----------------|-----------|
| **Flexibility** | Limited to predefined patterns | Works for ANY topic |
| **Maintainability** | Must update patterns constantly | Self-improving |
| **Accuracy** | Misses edge cases | Understands nuance |
| **Entity Types** | Universities, Companies only | People, places, concepts, etc. |
| **Ambiguity** | Rule-based (rigid) | Intelligent (context-aware) |
| **Development** | Slow (add patterns manually) | Fast (LLM learns) |

## Cost & Performance

### Cost Analysis
- **Model**: Gemini 1.5 Flash (fast & cheap)
- **Input**: ~500 tokens (conversation + prompt)
- **Output**: ~200 tokens (JSON response)
- **Cost per query**: ~$0.0001 (0.01 cents)
- **100 queries**: ~$0.01 (1 cent)

**Very affordable!**

### Performance
- **Entity extraction**: ~200-500ms (LLM call)
- **Query rewriting**: ~200-500ms (LLM call)
- **Total overhead**: ~400-1000ms

**Trade-off**: Slightly slower but MUCH more accurate and flexible

## Configuration

### Enable/Disable
```bash
# backend/.env
feature_corewrite=true  # Enable LLM-based context
```

### Environment Variables
```bash
GEMINI_API_KEY=your_key_here  # Required for LLM extraction
```

## Monitoring

### Logs to Watch
```bash
# Entity extraction
🧠 LLM extracted 3 entities: ['Albert Einstein', 'Theory of Relativity', '1905']

# Query rewriting
✏️  LLM rewrite: What did he discover?... → What did Albert Einstein discover?...
   Reasoning: Replaced 'he' with 'Albert Einstein' from context

# Ambiguity detected
🔍 LLM detected ambiguity: What did it invent?...
   Reason: Multiple companies mentioned (Apple, Microsoft)
```

## Example Conversations

### Example 1: Person Reference
```
User: "Tell me about Marie Curie"
AI: [Response about Marie Curie]

🧠 Extracted: [{"name": "Marie Curie", "type": "person"}]

User: "What did she discover?"
✏️  Rewrite: "What did she discover?" → "What did Marie Curie discover?"

AI: [Context-aware response] ✅
```

### Example 2: Concept Reference
```
User: "Explain machine learning"
AI: [Explanation of ML]

🧠 Extracted: [{"name": "machine learning", "type": "concept"}]

User: "How is that used in practice?"
✏️  Rewrite: "How is that used..." → "How is machine learning used in practice?"

AI: [Context-aware response] ✅
```

### Example 3: Book Reference
```
User: "Summarize 1984 by George Orwell"
AI: [Summary of 1984]

🧠 Extracted: [
  {"name": "1984", "type": "book"},
  {"name": "George Orwell", "type": "person"}
]

User: "Who wrote it?"
✏️  Rewrite: "Who wrote it?" → "Who wrote 1984?"

AI: "George Orwell wrote 1984" ✅
```

### Example 4: Ambiguity Handling
```
User: "Compare Apple and Microsoft"
AI: [Comparison]

🧠 Extracted: [
  {"name": "Apple", "type": "company"},
  {"name": "Microsoft", "type": "company"}
]

User: "What products does it make?"
🔍 LLM detected ambiguity!
   Options: ["Apple", "Microsoft"]
   Question: "Which company did you mean?"

[Disambiguation UI shown to user] ✅
```

## Fallback Behavior

If LLM extraction fails:
1. ✅ Falls back to original message (no rewriting)
2. ✅ Logs warning
3. ✅ Request continues normally

**Graceful degradation** - system never breaks!

## Future Enhancements

### Short-term
1. **Caching**: Cache entity extractions per thread (reduce LLM calls)
2. **Batch processing**: Extract entities once per 5-10 messages
3. **Model selection**: Allow choosing different LLMs (GPT-4o-mini, Claude)

### Long-term
1. **Multi-turn memory**: Remember entities across sessions
2. **User preferences**: Learn which entities user cares about
3. **Relationship tracking**: "Einstein's wife" → "Mileva Marić"
4. **Temporal understanding**: "yesterday's topic", "last week's discussion"

## Testing

### Test Scenario 1: Person
```bash
curl -X POST .../messages/stream \
  -d '{"content":"Tell me about Steve Jobs"}'

# Wait for response

curl -X POST .../messages/stream \
  -d '{"content":"What did he invent?"}'

# Expected: LLM rewrites to "What did Steve Jobs invent?"
```

### Test Scenario 2: Concept
```bash
curl -X POST .../messages/stream \
  -d '{"content":"Explain quantum computing"}'

curl -X POST .../messages/stream \
  -d '{"content":"How does that work?"}'

# Expected: "How does quantum computing work?"
```

### Test Scenario 3: Ambiguity
```bash
curl -X POST .../messages/stream \
  -d '{"content":"Compare Python and JavaScript"}'

curl -X POST .../messages/stream \
  -d '{"content":"Which is faster?"}'

# Expected: Disambiguation question!
```

## Comparison: Before vs After

### Before (Regex-based)
- ✅ Fast (~5ms overhead)
- ❌ Limited to hardcoded patterns
- ❌ Only works for universities, companies
- ❌ Misses: people, books, concepts, places
- ❌ Rigid ambiguity rules

### After (LLM-based)
- ⚠️ Slightly slower (~500ms overhead)
- ✅ Works for ANY topic
- ✅ Understands: people, books, concepts, dates, events, places
- ✅ Intelligent ambiguity detection
- ✅ Self-improving (better prompts = better results)

## Conclusion

**The LLM-based approach is MUCH more powerful!**

No more hardcoding patterns. The system now:
- 🧠 Understands ANY topic
- 🔄 Resolves ANY pronoun
- ❓ Detects ambiguity intelligently
- 📈 Improves with better prompts

**Ready to handle real-world conversations!** 🚀

---

## Quick Start

1. **Set API key**:
   ```bash
   echo "GEMINI_API_KEY=your_key" >> backend/.env
   ```

2. **Enable feature**:
   ```bash
   echo "feature_corewrite=true" >> backend/.env
   ```

3. **Restart backend**:
   ```bash
   # Auto-reloads if using --reload flag
   ```

4. **Test it**:
   ```bash
   # Message 1
   curl -X POST .../messages/stream -d '{"content":"Tell me about Einstein"}'

   # Message 2
   curl -X POST .../messages/stream -d '{"content":"What did he discover?"}'
   ```

5. **Check logs**:
   ```bash
   tail -f backend.log | grep "🧠\|✏️\|🔍"
   ```

**That's it!** Your AI is now context-aware for ANY topic! 🎉
