# Image Generation Debug Guide

## Recent Fixes Applied

1. ✅ **Intent Detection**: Now catches "just generate" and "nothing as such just generate"
2. ✅ **Context Awareness**: Uses previous AI message as prompt when user says "just generate"
3. ✅ **Provider Priority**: OpenAI DALL-E prioritized (more reliable than Gemini/Imagen)
4. ✅ **Fallback Logic**: If Gemini fails, automatically tries OpenAI
5. ✅ **Better Logging**: Added comprehensive logging throughout the flow

## How to Debug

### Step 1: Check Backend Logs

When you send "just generate" or "generate to me an image of X", look for these log messages:

```
🎨 Media generation intent detected: image, metadata: {...}
📝 Image generation prompt: '...'
🔍 Image generation check - Provider: openai, Has key: True, Available keys: ['openai']
🎨 Generating image with openai using prompt: '...'
```

### Step 2: Verify API Keys

Check if you have API keys configured:

**Option A: Environment Variables**
```bash
echo $OPENAI_API_KEY
echo $GOOGLE_API_KEY
```

**Option B: Check Backend Settings**
The logs will show: `Available keys: ['openai']` or `Available keys: []`

### Step 3: Test Intent Detection

You can test intent detection directly:

```python
from app.services.media_intent_detector import media_intent_detector

# Test "just generate"
intent, metadata = media_intent_detector.detect_intent(
    "just generate",
    previous_ai_message="A sunset with a sky painted in impossible hues..."
)
print(f"Intent: {intent}, Metadata: {metadata}")
```

### Step 4: Common Issues

**Issue 1: No API Key**
- **Symptom**: Logs show `Available keys: []`
- **Fix**: Set `OPENAI_API_KEY` environment variable or configure via API

**Issue 2: Intent Not Detected**
- **Symptom**: Logs show `No media generation intent detected`
- **Fix**: Use phrases like:
  - "generate to me an image of X"
  - "create an image of X"
  - "just generate" (after AI describes something)

**Issue 3: Image Generation Fails**
- **Symptom**: Logs show `Image generation returned None`
- **Check**: 
  - API key is valid
  - API key has image generation permissions
  - Network connectivity

**Issue 4: Media Event Not Sent**
- **Symptom**: Backend generates image but frontend doesn't show it
- **Check**: 
  - Frontend is using streaming endpoint (`/messages/stream`)
  - Frontend handles `event: media` events
  - Browser console for SSE events

## Testing Commands

Try these in order:

1. **Explicit request**:
   ```
   generate to me an image of a sunset
   ```

2. **After AI describes something**:
   ```
   AI: "A sunset with a sky painted in impossible hues..."
   You: "just generate"
   ```

3. **Simple request**:
   ```
   create an image of a robot
   ```

## What to Share for Debugging

If it's still not working, please share:

1. **Backend logs** - Look for lines starting with:
   - `🎨 Media generation intent detected`
   - `🔍 Image generation check`
   - `🎨 Generating image`
   - `✅ Image generated` or `⚠️ Image generation`

2. **API Key Status**:
   - Do you have `OPENAI_API_KEY` set?
   - Do you have `GOOGLE_API_KEY` set?

3. **Test Message**:
   - What exact message did you send?
   - What was the previous AI response (if any)?

4. **Frontend Console**:
   - Open browser DevTools → Console
   - Look for `🎨 Media event received` or errors

## Quick Fix: Ensure OpenAI API Key

The most reliable way to get image generation working:

```bash
# In backend directory
export OPENAI_API_KEY=sk-your-key-here

# Or add to .env file
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

Then restart the backend server.

