# Media Generation Feature

This document describes the image generation and matplotlib graph generation features added to Syntra.ai.

## Overview

The system now supports:
1. **Image Generation**: Using DALL-E (OpenAI) to generate images from text prompts
2. **Graph Generation**: Using matplotlib to create charts and graphs from data requests

## How It Works

### Intent Detection

The system automatically detects when users want to generate images or graphs by analyzing their messages for keywords:

**Image Generation Keywords:**
- "generate image", "create image", "draw", "picture", "photo", "illustration"
- "visualize", "show me an image", "make an image", "image of", "picture of"
- "dall-e", "dalle", "stable diffusion", "midjourney"

**Graph Generation Keywords:**
- "graph", "chart", "plot", "visualize", "show data", "display data"
- "line chart", "bar chart", "pie chart", "scatter plot", "area chart"
- "plot the data", "create a graph", "make a chart", "draw a graph"
- "visualization", "matplotlib", "show trends", "plot over time"

### Backend Implementation

#### Services Created

1. **`media_intent_detector.py`**: Detects user intent for image/graph generation
2. **`media_generation.py`**: Handles actual generation of images and graphs

#### Integration

The feature is integrated into the streaming endpoint (`/api/threads/{thread_id}/messages/stream`):
- Intent is detected before processing the message
- After the text response completes, media is generated in the background
- Media is sent as SSE events with type `media`

### Frontend Implementation

#### Updates Made

1. **`use-sse-chat.ts`**: Updated to handle `media` events from SSE stream
2. **`message-bubble.tsx`**: Updated to display generated images and graphs
3. **Message Interface**: Added `media` field to support images and graphs

## Usage Examples

### Image Generation

Users can request images with natural language:

```
"Generate an image of a futuristic city at sunset"
"Create a picture of a robot helping in a kitchen"
"Draw an illustration of a space station"
```

### Graph Generation

Users can request graphs with natural language:

```
"Create a graph showing sales over the last 6 months"
"Plot a bar chart of quarterly revenue"
"Show me a line graph of user growth"
```

The system will:
1. Detect the intent
2. Generate the appropriate media
3. Display it in the chat interface

## Technical Details

### Image Generation

- **Providers**: 
  - **Google Gemini/Imagen (Nano Banana Pro)** - Priority provider (if API key available)
  - **OpenAI DALL-E 3** - Fallback provider
- **Provider Selection**: Automatically selects best available provider:
  1. Gemini/Google (if API key available)
  2. OpenAI DALL-E 3
  3. Replicate (Stable Diffusion)
  4. Hugging Face
- **API Key Sources**: Checks multiple sources for API keys:
  - Current provider's API key (if Gemini or OpenAI)
  - Environment variables (`GOOGLE_API_KEY`, `OPENAI_API_KEY`)
  - Settings configuration
  - Database (per-org keys)
- **Format**: Returns image URL or base64 data URI
- **Aspect Ratio**: Defaults to 1:1, can be customized

**Note**: For full Gemini/Imagen support, you may need to configure Vertex AI project settings. The system will attempt to use the Generative AI API first, then fall back to other providers.

### Graph Generation

- **Library**: matplotlib
- **Supported Chart Types**:
  - Line charts
  - Bar charts
  - Pie charts
  - Scatter plots
  - Area charts
- **Data Extraction**: 
  - Attempts to extract data from user request
  - Falls back to sample data if extraction fails
  - Can accept structured data if provided
- **Styling**: Dark theme optimized for the UI

### API Keys

For image generation, you need an OpenAI API key configured. The system will:
1. Try to use the current provider's API key if it's OpenAI
2. Fall back to environment variables (`OPENAI_API_KEY`)
3. Check settings configuration
4. Query the database for per-organization keys

## Configuration

### Backend Requirements

Add to `requirements.txt`:
```
matplotlib
numpy
```

### Environment Variables

**For Image Generation:**

```bash
# Gemini/Imagen (Priority - recommended)
GOOGLE_API_KEY=your_google_api_key_here

# OpenAI DALL-E (Fallback)
OPENAI_API_KEY=your_openai_api_key_here
```

**Or configure via the API:**

```bash
# Gemini/Google
POST /api/orgs/{org_id}/provider-keys
{
  "provider": "google",
  "api_key": "your_google_api_key",
  "is_active": true
}

# OpenAI
POST /api/orgs/{org_id}/provider-keys
{
  "provider": "openai",
  "api_key": "sk-...",
  "is_active": true
}
```

**Note**: The system will automatically prefer Gemini/Imagen if available, falling back to OpenAI if not.

## Error Handling

- If image generation fails (e.g., no API key), the request continues normally
- Errors are logged but don't break the chat flow
- Users will see the text response even if media generation fails

## Future Enhancements

Potential improvements:
1. Support for more image generation providers (Stable Diffusion, Midjourney)
2. More sophisticated data extraction from user requests
3. Interactive graphs with zoom/pan capabilities
4. Graph customization options (colors, styles, themes)
5. Batch image generation
6. Image editing capabilities

## Testing

To test the feature:

1. **Image Generation**:
   ```
   "Generate an image of a beautiful sunset over mountains"
   ```

2. **Graph Generation**:
   ```
   "Create a line chart showing: Jan: 100, Feb: 120, Mar: 110, Apr: 140"
   ```

The system should automatically detect the intent and generate the appropriate media.

