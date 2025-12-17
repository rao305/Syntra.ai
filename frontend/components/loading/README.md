# Enhanced Loading State UI System

This directory contains the enhanced loading state components for Syntra AI, providing engaging and informative loading experiences for both collaboration and single-model modes.

## Components

### 1. LoadingState (Primary Component)

The main enhanced loading component with full support for collaboration mode tracking.

**Location:** `components/LoadingState.tsx`

**Features:**
- ✅ Collaboration mode with stage visualization
- ✅ Progress tracking and completion percentage
- ✅ Model attribution with icons
- ✅ Real-time elapsed timer
- ✅ Animated stage pipeline
- ✅ Rotating thinking messages
- ✅ Auto/Single mode support

**Usage:**

```tsx
import { LoadingState } from '@/components/LoadingState'

// Collaboration Mode
<LoadingState
  mode="collaborate"
  currentStage="analyst"
  currentModel="GPT-4o"
  stagesCompleted={2}
  totalStages={6}
  elapsedMs={3500}
  status="processing"
/>

// Auto/Single Mode
<LoadingState
  mode="auto"
  currentModel="Gemini 2.5 Flash"
  elapsedMs={1200}
  status="generating"
/>
```

**Props:**

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `mode` | `'auto' \| 'collaborate' \| 'single'` | Yes | Loading mode |
| `currentStage` | `string` | No | Current stage ID (for collaboration) |
| `currentModel` | `string` | No | Model name being used |
| `stagesCompleted` | `number` | No | Number of completed stages |
| `totalStages` | `number` | No | Total stages (default: 6) |
| `elapsedMs` | `number` | No | Elapsed time in milliseconds |
| `status` | `'selecting' \| 'processing' \| 'generating' \| 'synthesizing'` | No | Current status |

**Collaboration Stage IDs:**
- `analyst` - Analyzing Problem 🔍
- `researcher` - Researching 📚
- `creator` - Drafting Solution ✏️
- `critic` - Reviewing 🎯
- `council` - Council Deliberating ⚖️
- `synthesizer` - Synthesizing 🔬
- `judge` - Final Review ✅

---

### 2. SimpleLoadingState (Quick Alternative)

A simpler, lighter-weight loading component for basic use cases.

**Location:** `components/SimpleLoadingState.tsx`

**Features:**
- ✅ Rotating messages
- ✅ Model attribution
- ✅ Timer display
- ✅ Collaboration badge
- ✅ Minimal footprint

**Usage:**

```tsx
import { SimpleLoadingState } from '@/components/SimpleLoadingState'

<SimpleLoadingState
  model="GPT-4o"
  isCollaboration={true}
/>
```

**Props:**

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `model` | `string` | No | Model name |
| `isCollaboration` | `boolean` | No | Show collaboration badge |

---

### 3. SkeletonResponse

Skeleton loader showing placeholder for where the response will appear.

**Location:** `components/SkeletonResponse.tsx`

**Features:**
- ✅ Shimmer animation
- ✅ Text line placeholders
- ✅ Code block placeholder
- ✅ Responsive design

**Usage:**

```tsx
import { SkeletonResponse } from '@/components/SkeletonResponse'

<SkeletonResponse />
```

---

## Animations

All animations are defined in `styles/globals.css`:

### Available Animations

1. **`animate-bounce-slow`** - Slow vertical bounce for icons
2. **`animate-shimmer`** - Shimmer effect for skeleton loading
3. **`animate-glow-pulse`** - Glowing pulse for active stages
4. **`typing-indicator`** - Typing dots animation
5. **`delay-100`, `delay-200`** - Animation delay utilities

### Custom Keyframes

```css
@keyframes bounce-slow {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes glow-pulse {
  0%, 100% { box-shadow: 0 0 5px rgba(59, 130, 246, 0.5); }
  50% { box-shadow: 0 0 15px rgba(59, 130, 246, 0.8); }
}
```

---

## Integration Example

### In EnhancedChatInterface

```tsx
import { LoadingState } from '@/components/LoadingState'
import { useState, useEffect } from 'react'

export function EnhancedChatInterface({ isLoading, isCollaborateMode, steps }) {
  const [loadingStartTime, setLoadingStartTime] = useState(0)
  const [elapsedMs, setElapsedMs] = useState(0)

  // Track loading time
  useEffect(() => {
    if (isLoading) {
      setLoadingStartTime(Date.now())
    } else {
      setElapsedMs(0)
      setLoadingStartTime(0)
    }
  }, [isLoading])

  // Update elapsed time
  useEffect(() => {
    if (!isLoading || loadingStartTime === 0) return

    const interval = setInterval(() => {
      setElapsedMs(Date.now() - loadingStartTime)
    }, 100)

    return () => clearInterval(interval)
  }, [isLoading, loadingStartTime])

  return (
    <div>
      {/* Your messages */}

      {isLoading && (
        <LoadingState
          mode={isCollaborateMode ? 'collaborate' : 'auto'}
          currentStage={/* Get from active step */}
          currentModel={/* Get from active step or selected model */}
          stagesCompleted={/* Count completed steps */}
          totalStages={steps.length || 6}
          elapsedMs={elapsedMs}
          status="processing"
        />
      )}
    </div>
  )
}
```

---

## Model Icons

The loading states automatically show model-specific icons:

| Model | Icon | Color |
|-------|------|-------|
| GPT/OpenAI | 🟢 | Green |
| Gemini | 🔵 | Blue |
| Claude | 🟣 | Purple |
| Perplexity | 🟠 | Orange |
| Other | 🤖 | Gray |

---

## Responsive Design

All loading components are responsive and work across:
- Desktop (full width, max 90%)
- Tablet (adjusted spacing)
- Mobile (stacked layout)

---

## Performance

- **Minimal re-renders**: Uses memoization and stable state
- **Efficient animations**: CSS-based, GPU-accelerated
- **Timer optimization**: Updates every 100ms (not every frame)
- **Lazy loading**: Components only render when visible

---

## Customization

### Changing Stage Labels

Edit `STAGE_LABELS` in `LoadingState.tsx`:

```tsx
const STAGE_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  'analyst': { label: 'Your Custom Label', icon: '🔍', color: 'text-blue-400' },
  // ...
}
```

### Adding New Messages

Edit `THINKING_MESSAGES` or `MODEL_MESSAGES` arrays:

```tsx
const THINKING_MESSAGES = [
  "Analyzing your request...",
  "Your custom message...",
  // ...
]
```

### Customizing Colors

Modify Tailwind classes in the component:
- `from-purple-500 to-blue-500` - Gradient colors
- `text-gray-300` - Text color
- `bg-gray-800/50` - Background color

---

## Testing Checklist

- ✅ Loading appears when sending message
- ✅ Collaboration mode shows stage progress
- ✅ Model name displays correctly
- ✅ Timer updates in real-time
- ✅ Animations are smooth
- ✅ Loading disappears when response arrives
- ✅ Works for quick responses (<1s)
- ✅ Works for long responses (30s+)
- ✅ Doesn't block streaming text
- ✅ Mobile responsive

---

## Troubleshooting

### Loading state doesn't appear
- Check `isLoading` prop is true
- Verify component is mounted in DOM
- Check CSS animations are loaded

### Timer not updating
- Verify `elapsedMs` is being updated via useEffect
- Check interval is not being cleared prematurely

### Animations stuttering
- Reduce animation complexity
- Check for heavy re-renders in parent
- Use React DevTools Profiler

### Stage not updating in collaboration mode
- Verify `currentStage` prop is changing
- Check `steps` data structure is correct
- Console.log the active stage ID

---

## Future Enhancements

Potential improvements:
- [ ] Sound effects for stage transitions
- [ ] More granular progress within each stage
- [ ] Estimated time remaining
- [ ] Cancel/pause button
- [ ] Quality metrics preview
- [ ] Model switching visualization
- [ ] WebSocket live updates

---

## Support

For issues or questions:
1. Check this README
2. Review component source code
3. Check console for errors
4. Verify props being passed
5. Test with SimpleLoadingState for comparison

---

**Last Updated:** December 2025
**Version:** 1.0.0
**Author:** Syntra AI Team
