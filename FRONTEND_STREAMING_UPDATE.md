# Frontend Streaming Update - Image Generation Support

## Summary

Updated the frontend conversation page to use the streaming endpoint and handle media events for image/graph generation.

## Changes Made

### 1. Updated Message Interface
- Added `media` field to support generated images and graphs
- Type: `Array<{ type: 'image' | 'graph'; url: string; alt?: string; mime_type?: string }>`

### 2. Switched to Streaming Endpoint
- **Before**: Used non-streaming `/threads/{threadId}/messages`
- **After**: Uses streaming `/threads/{threadId}/messages/stream`
- Enables real-time text streaming and media event reception

### 3. Added SSE Event Handler
Handles the following events:
- `event: router` - Provider/model information
- `event: delta` - Text content chunks (streaming)
- `event: media` - Generated images/graphs
- `event: done` - Stream completion
- `event: error` - Error handling

### 4. Added updateMessage Helper
- Function to update messages in real-time as events arrive
- Supports function-based updates (e.g., `content: (prev) => prev + delta`)
- Handles media array updates

### 5. Real-time Message Updates
- Messages update as content streams in
- Media is added to messages when `event: media` is received
- Final metadata (reasoning type, confidence, etc.) is added after stream completes

## How It Works

1. **User sends message** → Frontend creates user message
2. **Streaming starts** → Frontend creates placeholder assistant message
3. **Events stream in**:
   - `delta` events → Update message content in real-time
   - `media` events → Add images/graphs to message
   - `done` event → Finalize message with metadata
4. **Message bubble displays** → Shows text + generated media

## Testing

Test with:
- "generate to me an image of doremon"
- "create an image of a sunset"
- "generate a graph showing sales data"

The system should now:
1. ✅ Detect image generation intent
2. ✅ Stream text response
3. ✅ Generate image in background
4. ✅ Send media event via SSE
5. ✅ Display image in message bubble

## Files Modified

- `frontend/app/conversations/page.tsx` - Main conversation page with streaming support
- `frontend/components/message-bubble.tsx` - Already had media display (no changes needed)

## Backend Requirements

- Streaming endpoint: `/api/threads/{thread_id}/messages/stream`
- Media events: `event: media` with image/graph data
- API keys: Gemini/Google or OpenAI configured

## Status

✅ **Complete** - Frontend now fully supports image generation via streaming!

