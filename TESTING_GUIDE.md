# Testing Guide - Your Chats Feature

## Quick Test Checklist

### ✅ Pre-Testing Setup

1. **Verify Migration Applied:**
   ```bash
   cd backend
   source venv/bin/activate
   alembic current
   # Should show: 010 (head)
   ```

2. **Start Backend Server:**
   ```bash
   cd backend
   source venv/bin/activate
   python main.py
   # Server should start on http://localhost:8000
   ```

3. **Start Frontend (in separate terminal):**
   ```bash
   cd frontend
   npm run dev
   # Frontend should start on http://localhost:3000
   ```

---

## Backend API Testing

### Test 1: List Threads (with archived filter)
```bash
curl -X GET "http://localhost:8000/api/threads?limit=10" \
  -H "x-org-id: org_demo"
```

**Expected:** List of threads (non-archived by default)

### Test 2: Search Threads
```bash
curl -X GET "http://localhost:8000/api/threads/search?q=test&limit=10" \
  -H "x-org-id: org_demo"
```

**Expected:** Threads matching "test" in title or preview

### Test 3: Archive Thread
```bash
# First, get a thread ID from list endpoint, then:
curl -X PATCH "http://localhost:8000/api/threads/{THREAD_ID}/archive" \
  -H "x-org-id: org_demo" \
  -H "Content-Type: application/json" \
  -d '{"archived": true}'
```

**Expected:** `{"success": true, "thread_id": "...", "archived": true, ...}`

### Test 4: Unarchive Thread
```bash
curl -X PATCH "http://localhost:8000/api/threads/{THREAD_ID}/archive" \
  -H "x-org-id: org_demo" \
  -H "Content-Type: application/json" \
  -d '{"archived": false}'
```

### Test 5: List Archived Threads
```bash
curl -X GET "http://localhost:8000/api/threads?archived=true" \
  -H "x-org-id: org_demo"
```

**Expected:** Only archived threads

---

## Frontend Testing

### Test 1: View Sidebar
1. Navigate to http://localhost:3000/conversations
2. **Check:** Sidebar should show:
   - Search bar at top
   - "New chat" button
   - Threads organized by date (if any exist)

### Test 2: Search Functionality
1. Type in search bar
2. **Check:** 
   - Debounced search (waits 300ms)
   - Shows "Search results" section
   - Filters threads as you type

### Test 3: Thread Actions (Right-Click)
1. Right-click on any thread
2. **Check:** Context menu appears with:
   - Rename
   - Pin/Unpin
   - Archive/Unarchive
   - Delete

### Test 4: Rename Thread
1. Right-click thread → Rename
2. Edit title inline
3. Press Enter or click outside
4. **Check:** Title updates, toast notification appears

### Test 5: Pin Thread
1. Right-click thread → Pin
2. **Check:** 
   - Thread moves to "Pinned" section
   - Pin icon appears
   - Toast notification

### Test 6: Archive Thread
1. Right-click thread → Archive
2. **Check:**
   - Thread disappears from main list
   - Toast notification
   - Can unarchive from search if needed

### Test 7: Delete Thread
1. Right-click thread → Delete
2. Confirm deletion
3. **Check:**
   - Thread removed from list
   - Confirmation dialog appeared
   - Toast notification

### Test 8: Date Grouping
1. Have threads from different dates
2. **Check:** Threads grouped into:
   - Today
   - Yesterday
   - Previous 7 days
   - Previous 30 days
   - Older

---

## Integration Testing

### Test 1: Create Thread & See in Sidebar
1. Click "New chat"
2. Send a message
3. **Check:** New thread appears in sidebar

### Test 2: Navigate Between Threads
1. Click different threads in sidebar
2. **Check:** 
   - Active thread highlights
   - Messages load correctly
   - URL updates

### Test 3: Search & Navigate
1. Search for a thread
2. Click search result
3. **Check:** Navigates to correct thread

---

## Browser Console Testing

Open browser DevTools console and check for:
- ✅ No errors when loading sidebar
- ✅ API calls succeeding (check Network tab)
- ✅ Search debouncing working
- ✅ Optimistic updates happening

---

## Quick Test Script

Save this as `test_your_chats.sh`:

```bash
#!/bin/bash
ORG_ID="org_demo"
BASE_URL="http://localhost:8000/api"

echo "🧪 Testing Your Chats Feature"
echo "=============================="

# Test 1: List threads
echo -e "\n1️⃣ Testing: List Threads"
curl -s -X GET "${BASE_URL}/threads?limit=5" \
  -H "x-org-id: ${ORG_ID}" | jq '.[0:2]' || echo "❌ Failed"

# Test 2: Search (will fail if no threads, that's ok)
echo -e "\n2️⃣ Testing: Search Threads"
curl -s -X GET "${BASE_URL}/threads/search?q=test&limit=5" \
  -H "x-org-id: ${ORG_ID}" | jq '.' || echo "❌ No results (ok if no threads)"

# Test 3: Check health
echo -e "\n3️⃣ Testing: Backend Health"
curl -s -X GET "http://localhost:8000/health" | jq '.' || echo "❌ Backend not running"

echo -e "\n✅ Basic tests complete!"
```

---

## Manual Testing Steps

1. **Start Services:**
   - Backend: `cd backend && source venv/bin/activate && python main.py`
   - Frontend: `cd frontend && npm run dev`

2. **Create Test Data:**
   - Create a few conversations
   - Send messages to generate thread titles

3. **Test Features:**
   - Search for conversations
   - Pin a conversation
   - Archive a conversation
   - Rename a conversation
   - Delete a conversation
   - Check date grouping

4. **Verify:**
   - All actions show toast notifications
   - Sidebar updates correctly
   - No console errors
   - API calls succeed

