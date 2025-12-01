---
title: Quick Start Guide - New DAC Conversation Interface
summary: Documentation file
last_updated: '2025-11-12'
owner: DAC
tags:
- dac
- docs
---

# Quick Start Guide - New DAC Conversation Interface

## 🚀 Getting Started

### 1. Access the New Interface
```bash
# Visit in your browser:
http://localhost:3000/conversations
```

### 2. First Time Setup

The interface will show:
- **Left Sidebar**: Conversation list (currently empty)
- **Center Panel**: Welcome screen with example prompts
- **Right Sidebar**: Settings panel (model selection, system prompt, parameters)

### 3. Start Your First Conversation

**Option A**: Click an example prompt card
- Choose from 4 categories: Creative, Technical, Analysis, Learning
- The prompt will auto-fill in the composer

**Option B**: Type your own message
- Click in the message composer at the bottom
- Type your question or request
- Press `Cmd+Enter` (Mac) or `Ctrl+Enter` (Windows) to send

### 4. Explore the Interface

**Left Sidebar**:
- Click `+` button to create new conversation
- Use search box to filter conversations (`Cmd/Ctrl+F`)
- Click any conversation to open it

**Center Panel**:
- View message history
- Hover over messages to see actions (copy, regenerate, edit, delete)
- Scroll to see older messages
- Type in the multiline composer

**Right Sidebar**:
- **Settings Tab**:
  - Select which AI models to use
  - Edit system prompt (instructions for AI)
  - Adjust temperature (0-2, creativity level)
  - Set max tokens (response length)
- **Context Tab**:
  - View token usage
  - Manage context documents (coming soon)

### 5. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + N` | New conversation |
| `Cmd/Ctrl + F` | Search conversations |
| `Cmd/Ctrl + Enter` | Send message |
| `Cmd/Ctrl + ,` | Toggle settings panel |
| `Escape` | Cancel/Close |

---

## 🎨 Customization

### Adjust Panel Sizes
- **Drag the handles** between panels to resize
- Your sizes are saved automatically
- **Double-click a handle** to collapse/expand a panel

### Change Theme
- Click the **theme icon** (sun/moon) in the header
- Choose: Light, Dark, or System

### Configure AI Behavior
1. Open **Settings Panel** (right sidebar)
2. Go to **Settings tab**
3. Adjust:
   - **Temperature**: Higher = more creative, Lower = more focused
   - **Max Tokens**: Longer responses vs. shorter responses
   - **System Prompt**: Custom instructions for AI behavior

---

## 💡 Tips & Tricks

### Efficient Workflow
1. Use keyboard shortcuts instead of clicking
2. Keep settings panel open for quick model switching
3. Use search to find old conversations quickly
4. Try example prompts to explore capabilities

### Best Practices
- **Start simple**: Begin with clear, specific questions
- **Iterate**: Use regenerate button to try different responses
- **Experiment**: Try different temperature settings for different tasks
- **Organize**: Create new conversations for different topics

### Common Tasks

**Copy a response**:
- Hover over any message
- Click the copy icon (clipboard)
- Success notification will appear

**Regenerate a response**:
- Hover over an AI message
- Click the regenerate icon (refresh)
- New response will replace the old one

**Edit your message**:
- Hover over your message
- Click the edit icon (pencil)
- Modify and re-send

**Delete a message**:
- Hover over any message
- Click the more icon (three dots)
- Select "Delete"

---

## 🔧 Troubleshooting

### Page Not Loading
```bash
# Check if frontend is running:
curl http://localhost:3000/conversations

# If not, start it:
cd /Users/rao305/Documents/DAC/frontend
npm run dev
```

### Backend Not Responding
```bash
# Check if backend is running:
curl http://localhost:8000/health

# Should return: {"status":"healthy"}
```

### Messages Not Sending
1. Check for error banner at top of page
2. Common issues:
   - Rate limit exceeded: Wait and try again
   - No API keys configured: Add provider keys in settings
   - Network error: Check backend is running

### Settings Not Saving
- System prompt changes: Click "Save Changes" button
- Panel sizes: Auto-saved on every resize
- Theme preference: Auto-saved immediately

---

## 📚 Documentation

### Full Documentation
- **Component Docs**: `frontend/COMPONENTS_DOCUMENTATION.md`
- **Implementation Summary**: `UI_IMPLEMENTATION_COMPLETE.md`
- **Smoke Test Results**: `SMOKE_TEST_RESULTS.md`

### Component Reference
All components are in `frontend/components/`:
- `conversation-layout.tsx` - Main 3-pane layout
- `conversation-list.tsx` - Left sidebar
- `message-bubble.tsx` - Message display
- `message-composer.tsx` - Input area
- `settings-panel.tsx` - Right sidebar
- And 7 more...

---

## 🎯 Next Steps

### Try These Features
1. ✅ Create your first conversation
2. ✅ Send a message and get a response
3. ✅ Copy a message
4. ✅ Try different models
5. ✅ Adjust temperature settings
6. ✅ Search conversations
7. ✅ Use keyboard shortcuts
8. ✅ Toggle theme

### Explore Advanced Features
- Edit system prompt for custom AI behavior
- Compare responses from different models
- Organize conversations by topic
- Experiment with temperature settings

---

## 🆘 Need Help?

### Check These First
1. Browser console for errors (F12 → Console)
2. Network tab for failed requests (F12 → Network)
3. Backend logs for API errors

### Common Solutions
- **Refresh the page**: Solves most temporary issues
- **Clear localStorage**: If panel sizes are stuck
- **Check backend logs**: For API errors
- **Verify API keys**: In provider settings

---

## ✨ Feature Highlights

### What Makes This Special
- **3-Pane Layout**: See everything at once
- **Smart Routing**: AI automatically chooses best model
- **Multiple Models**: Compare responses side-by-side
- **Persistent State**: All your settings saved
- **Keyboard First**: Work faster with shortcuts
- **Beautiful UX**: Polished, professional interface
- **Fully Accessible**: Screen reader compatible

---

**Status**: Production Ready
**Version**: 1.0
**Last Updated**: November 9, 2025

Enjoy your new conversation interface! 🎉
