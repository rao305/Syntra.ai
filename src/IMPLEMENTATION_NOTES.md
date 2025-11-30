# Implementation Notes

## Architecture Decisions

### 1. In-Memory HistoryStore
- **Current**: Uses `Map<string, ConversationHistory>` for simplicity
- **Future**: Can be swapped to Redis/PostgreSQL by implementing the same interface
- **Why**: Fast development, easy to test, production-ready abstraction

### 2. Entity Resolver as Micro-Agent
- **Separate LLM call**: Uses dedicated system prompt and model
- **JSON output**: Forces structured response for reliability
- **Fallback strategy**: Always returns original message on error (never fails silently)

### 3. Context Window Management
- **Rolling window**: Last N messages (default 20)
- **System prompt**: Always included, managed by ContextManager
- **Resolved query replacement**: Last user message replaced with resolved query before sending to main LLM

### 4. Provider Abstraction
- **Interface-based**: All providers implement `LlmProviderInterface`
- **Normalized response**: All providers return `{ content: string, raw?: any }`
- **Extensible**: Easy to add new providers via `registerProvider()`

## Flow Diagram

```
User Request
    ↓
/api/chat endpoint
    ↓
1. ContextManager.addUserMessage() → HistoryStore
    ↓
2. ContextManager.getRecentMessages() → Last 10 messages
    ↓
3. EntityResolver.resolve() → Rewrites "he" → "Donald Trump"
    ↓
4. ContextManager.getContextWindow() → Last 20 messages
    ↓
5. Build LLM messages: [system, ...history, resolvedQuery]
    ↓
6. LlmRouter.routeChat() → OpenAIProvider.chat()
    ↓
7. ContextManager.addAssistantMessage() → HistoryStore
    ↓
8. Return { answer, resolvedQuery, entities, providerUsed }
```

## Key Design Patterns

### Singleton Services
- `historyStore`: Single instance shared across requests
- `entityResolver`: Single instance for consistency
- `llmRouter`: Single instance with provider registry

### Error Handling Strategy
- **EntityResolver**: Always falls back to original message
- **LLM calls**: Errors bubble up with context
- **API endpoint**: Returns 500 with error message (never exposes internals)

### Type Safety
- All interfaces in `types.ts`
- Strict TypeScript configuration
- No `any` types except for `raw` field in responses

## Testing the Implementation

### Manual Test Flow

1. **Start with explicit entity:**
   ```json
   POST /api/chat
   {
     "sessionId": "test-123",
     "message": "Who is Donald Trump?",
     "provider": "openai"
   }
   ```

2. **Follow-up with pronoun:**
   ```json
   POST /api/chat
   {
     "sessionId": "test-123",
     "message": "When was he born?",
     "provider": "openai"
   }
   ```

3. **Expected response:**
   ```json
   {
     "answer": "Donald Trump was born on June 14, 1946.",
     "resolvedQuery": "When was Donald Trump born?",
     "entities": ["Donald Trump"],
     "providerUsed": "openai"
   }
   ```

## Production Considerations

### 1. HistoryStore Persistence
- **Current**: In-memory (lost on restart)
- **Production**: Redis or PostgreSQL
- **Migration**: Implement same interface, swap implementation

### 2. Rate Limiting
- Add middleware for `/api/chat` endpoint
- Per-user or per-session limits
- Consider token-based limits

### 3. Caching
- Cache entity resolutions for common queries
- Cache LLM responses (with session context awareness)
- TTL-based invalidation

### 4. Monitoring
- Log entity resolution success rate
- Track provider response times
- Monitor token usage per provider

### 5. History Summarization
- When context exceeds token limit, summarize older messages
- Keep recent messages verbatim
- Add summary as system message

## Extending the System

### Adding a New Provider

1. Create provider class:
   ```typescript
   export class NewProvider implements LlmProviderInterface {
     async chat(args) {
       // Implementation
     }
   }
   ```

2. Register in `LlmRouter`:
   ```typescript
   this.providers.set("newprovider", new NewProvider());
   ```

3. Update types:
   ```typescript
   provider: "openai" | "anthropic" | "gemini" | "perplexity" | "newprovider"
   ```

### Adding History Summarization

1. Implement in `ContextManager`:
   ```typescript
   async summarizeHistory(sessionId: string): Promise<void> {
     // Get old messages
     // Call LLM to summarize
     // Replace old messages with summary
   }
   ```

2. Call before `getContextWindow()` if token limit exceeded

### Adding Streaming Support

1. Modify `LlmProviderInterface`:
   ```typescript
   chatStream(args): AsyncIterable<string>
   ```

2. Update endpoint to use `StreamingResponse`
3. Handle entity resolution before streaming starts








