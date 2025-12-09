# Implementation Guide: ChatGPT-Style "Your Chats" Feature

## Overview

This guide explains how to implement a ChatGPT-style "Your Chats" sidebar feature that stores and manages previous conversations. Your codebase already has the foundation in place, but needs enhancements to match ChatGPT's functionality.

## Current State Analysis

### ✅ What You Already Have

1. **Database Models** (`backend/app/models/thread.py`):
   - `Thread` model with fields: `id`, `title`, `last_message_preview`, `pinned`, `created_at`, `updated_at`
   - `Message` model linked to threads
   - Basic thread storage and retrieval

2. **Backend API** (`backend/app/api/threads.py`):
   - `GET /api/threads/` - List threads (sorted by updated_at)
   - `GET /api/threads/{thread_id}` - Get thread details with messages
   - `PATCH /api/threads/{thread_id}` - Update thread title
   - `POST /api/threads/` - Create new thread

3. **Frontend Components**:
   - `EnhancedSidebar` component with basic history display
   - `useThreads` hook for fetching threads
   - Basic conversation routing

### ❌ What's Missing for Full ChatGPT Experience

1. **Thread Management**:
   - Delete/archive threads
   - Auto-generate thread titles from first message
   - Search/filter threads
   - Folder/category organization
   - Export conversations

2. **UI/UX Enhancements**:
   - Rich sidebar with search bar
   - Thread preview cards with last message
   - Edit thread titles inline
   - Context menu for thread actions
   - Better date formatting (Today, Yesterday, etc.)
   - Pinned threads section
   - Thread count/statistics

3. **Real-time Updates**:
   - Auto-refresh sidebar when new threads created
   - Update thread previews when messages added
   - Optimistic UI updates

---

## Implementation Roadmap

### Phase 1: Backend Enhancements

#### 1.1 Add Thread Deletion Endpoint

**Location**: `backend/app/api/threads.py`

**What to add**:
```python
@router.delete("/{thread_id}")
async def delete_thread(
    thread_id: str,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete a thread and all its messages."""
    # Implementation here
```

**Database**: 
- Threads already have `CASCADE` delete for messages (in Thread model relationships)
- This should work automatically when thread is deleted

#### 1.2 Add Thread Search Endpoint

**Location**: `backend/app/api/threads.py`

**What to add**:
```python
@router.get("/search")
async def search_threads(
    q: str,  # search query
    limit: int = 50,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """Search threads by title or message content."""
    # Full-text search on title and last_message_preview
    # Use PostgreSQL's full-text search capabilities
```

**Database Considerations**:
- Add full-text search index on `threads.title` and `threads.last_message_preview`
- Or search through `messages.content` for comprehensive search

#### 1.3 Auto-Generate Thread Titles

**Location**: `backend/app/api/threads.py` (in message creation endpoint)

**What to add**:
- When first message is sent to a thread without title:
  - Use LLM to generate a title from first user message
  - Or use simple truncation: first 50 characters of first message
  - Update thread title automatically

**Implementation**:
- Modify the message creation endpoint (`POST /api/threads/{thread_id}/messages`)
- Check if thread.title is None or empty
- Generate title using first user message content

#### 1.4 Update Thread Last Message Preview

**Location**: `backend/app/api/threads.py` (in message creation endpoint)

**What to add**:
- When new message is added, update `thread.last_message_preview`
- Update `thread.updated_at` timestamp (should already happen)
- Store preview (first 100 chars of last user message)

**Implementation**:
- After saving message, update thread:
  ```python
  thread.last_message_preview = message.content[:100]
  thread.updated_at = datetime.utcnow()
  ```

#### 1.5 Add Thread Archiving

**Location**: `backend/app/models/thread.py`

**What to add**:
- Add `archived` Boolean column to Thread model
- Add `archived_at` DateTime column (optional)
- Create migration to add columns

**API Endpoint**:
```python
@router.patch("/{thread_id}/archive")
async def archive_thread(thread_id: str, archived: bool, ...):
    """Archive or unarchive a thread."""
```

#### 1.6 Add Thread Statistics

**Location**: `backend/app/api/threads.py`

**What to add**:
```python
@router.get("/stats")
async def get_thread_stats(
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """Get thread statistics: total count, recent count, etc."""
```

---

### Phase 2: Database Migrations

#### 2.1 Create Migration for New Fields

**Location**: `backend/migrations/`

**What to add**:
1. `archived` column on threads table
2. `archived_at` column on threads table
3. Full-text search index on `title` and `last_message_preview`

**Migration File**: Create using Alembic:
```bash
cd backend
alembic revision -m "add_thread_archiving_and_search"
```

**SQL Example**:
```sql
ALTER TABLE threads ADD COLUMN archived BOOLEAN DEFAULT FALSE;
ALTER TABLE threads ADD COLUMN archived_at TIMESTAMPTZ;
CREATE INDEX idx_threads_fulltext_search ON threads USING gin(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(last_message_preview, '')));
```

---

### Phase 3: Frontend Enhancements

#### 3.1 Enhanced Sidebar Component

**Location**: `frontend/components/enhanced-sidebar.tsx`

**What to enhance**:
1. **Add Search Bar**:
   - Search input at top of sidebar
   - Real-time filtering of visible threads
   - Debounced API search for large datasets

2. **Add Thread Actions Menu**:
   - Right-click or three-dot menu on each thread
   - Options: Rename, Archive, Delete, Pin/Unpin
   - Copy thread link

3. **Better Date Formatting**:
   - "Today", "Yesterday", "Last week", "Older"
   - Group threads by date sections

4. **Pinned Section**:
   - Separate section for pinned threads at top
   - Always visible when sidebar is expanded

5. **Thread Preview Cards**:
   - Show last message preview
   - Show model/provider badge
   - Show message count (optional)

**New Component Structure**:
```
EnhancedSidebar
├── SearchBar
├── PinnedThreads (if any)
├── RecentThreads (grouped by date)
│   ├── ThreadItem (with context menu)
│   └── ThreadItem
└── Footer
```

#### 3.2 Thread Item Component

**Location**: `frontend/components/thread-item.tsx` (new file)

**What to create**:
- Reusable thread item component
- Shows title, preview, timestamp
- Inline title editing
- Context menu for actions
- Loading/error states

**Features**:
- Click to navigate
- Double-click or edit button to rename
- Hover to show actions
- Active state when current thread

#### 3.3 Thread Management Hook

**Location**: `frontend/hooks/use-threads.ts` (enhance existing)

**What to add**:
1. **Delete Thread**:
   ```typescript
   const deleteThread = async (threadId: string) => {
     await apiFetch(`/threads/${threadId}`, orgId, {
       method: 'DELETE'
     });
     await mutate(); // Refresh list
   };
   ```

2. **Archive Thread**:
   ```typescript
   const archiveThread = async (threadId: string, archived: boolean) => {
     await apiFetch(`/threads/${threadId}/archive`, orgId, {
       method: 'PATCH',
       body: JSON.stringify({ archived })
     });
     await mutate();
   };
   ```

3. **Search Threads**:
   ```typescript
   const searchThreads = async (query: string) => {
     const response = await apiFetch(`/threads/search?q=${query}`, orgId);
     return response.json();
   };
   ```

4. **Update Title**:
   ```typescript
   const updateTitle = async (threadId: string, title: string) => {
     await apiFetch(`/threads/${threadId}`, orgId, {
       method: 'PATCH',
       body: JSON.stringify({ title })
     });
     await mutate();
   };
   ```

#### 3.4 Real-time Updates

**Location**: `frontend/app/conversations/page.tsx`

**What to add**:
1. **Auto-refresh on New Thread**:
   - When new thread created, refresh sidebar
   - Use optimistic updates for instant UI feedback

2. **Update Thread Preview**:
   - When message sent, update thread in sidebar
   - Update `last_message_preview` and timestamp

3. **WebSocket/SSE for Real-time** (optional):
   - Subscribe to thread updates
   - Push updates to sidebar without refresh

#### 3.5 Search Functionality

**Location**: `frontend/components/chat-search.tsx` (new file)

**What to create**:
- Search input component
- Debounced search API calls
- Search results display
- Highlight matching text
- Keyboard shortcuts (Cmd+K to focus)

---

### Phase 4: UI/UX Polish

#### 4.1 Date Formatting Utility

**Location**: `frontend/lib/date-utils.ts` (new file)

**What to create**:
```typescript
export function formatThreadDate(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return date.toLocaleDateString();
}

export function groupThreadsByDate(threads: Thread[]): Record<string, Thread[]> {
  // Group threads by date sections
}
```

#### 4.2 Context Menu Component

**Location**: `frontend/components/thread-context-menu.tsx` (new file)

**What to create**:
- Dropdown menu on thread item
- Actions: Rename, Pin, Archive, Delete
- Keyboard shortcuts
- Confirmation dialogs for destructive actions

#### 4.3 Empty States

**What to add**:
- Empty state when no threads
- Empty state when search returns no results
- Loading skeleton states

---

## Detailed Implementation Steps

### Step 1: Backend - Thread Deletion

1. **Add DELETE endpoint** in `backend/app/api/threads.py`:
   - Verify thread belongs to org
   - Delete thread (messages cascade automatically)
   - Return success response

2. **Add soft delete option** (optional):
   - Instead of hard delete, mark as deleted
   - Filter deleted threads from list endpoint

### Step 2: Backend - Auto Title Generation

1. **Modify message creation endpoint**:
   - Check if thread has no title
   - Extract first user message
   - Generate title (simple or LLM-based)
   - Update thread title

2. **Title generation options**:
   - **Simple**: First 50 characters of first message
   - **LLM-based**: Use OpenAI/Gemini to generate descriptive title
   - **Hybrid**: Simple for now, upgrade to LLM later

### Step 3: Frontend - Enhanced Sidebar

1. **Add search bar**:
   - Input field at top
   - Debounce search (300ms)
   - Filter local threads first, then API search

2. **Group threads by date**:
   - Separate sections: Today, Yesterday, Previous 7 days, Older
   - Collapsible date sections

3. **Add thread actions**:
   - Three-dot menu on each thread
   - Context menu with actions
   - Confirmation for delete

### Step 4: Real-time Updates

1. **Update sidebar on thread creation**:
   - After creating thread, refresh sidebar
   - Optimistic add (show immediately)

2. **Update thread preview on message**:
   - After sending message, update thread in sidebar
   - Update last_message_preview and timestamp

3. **Polling or WebSocket** (optional):
   - Poll for thread updates every 30s
   - Or use WebSocket for real-time

---

## Database Schema Changes

### Current Thread Schema
```sql
CREATE TABLE threads (
  id VARCHAR PRIMARY KEY,
  org_id VARCHAR NOT NULL,
  creator_id VARCHAR,
  title VARCHAR,
  description TEXT,
  last_message_preview VARCHAR,
  pinned BOOLEAN DEFAULT FALSE,
  settings JSON,
  last_provider VARCHAR,
  last_model VARCHAR,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ
);
```

### Required Additions
```sql
-- Add archiving support
ALTER TABLE threads ADD COLUMN archived BOOLEAN DEFAULT FALSE;
ALTER TABLE threads ADD COLUMN archived_at TIMESTAMPTZ;

-- Add full-text search index
CREATE INDEX idx_threads_fulltext_search 
ON threads USING gin(
  to_tsvector('english', 
    coalesce(title, '') || ' ' || 
    coalesce(last_message_preview, '')
  )
);

-- Index for filtering archived threads
CREATE INDEX idx_threads_org_archived_updated 
ON threads (org_id, archived, updated_at DESC) 
WHERE archived = FALSE;
```

---

## API Endpoints Summary

### Existing Endpoints (Already Implemented)
- `GET /api/threads/` - List threads
- `GET /api/threads/{thread_id}` - Get thread details
- `POST /api/threads/` - Create thread
- `PATCH /api/threads/{thread_id}` - Update thread title

### New Endpoints Needed

1. **Thread Management**:
   - `DELETE /api/threads/{thread_id}` - Delete thread
   - `PATCH /api/threads/{thread_id}/archive` - Archive/unarchive
   - `PATCH /api/threads/{thread_id}/pin` - Pin/unpin (may already exist via settings)

2. **Search & Filter**:
   - `GET /api/threads/search?q={query}` - Search threads
   - `GET /api/threads?archived=true` - Filter archived threads
   - `GET /api/threads?pinned=true` - Get pinned threads

3. **Statistics**:
   - `GET /api/threads/stats` - Get thread statistics

---

## File Structure

### Backend Files to Modify
```
backend/
├── app/
│   ├── api/
│   │   └── threads.py                    # Add new endpoints
│   ├── models/
│   │   └── thread.py                     # Add archived fields (optional)
│   └── services/
│       └── thread_title_generator.py     # NEW: Auto title generation
└── migrations/
    └── versions/
        └── XXXX_add_thread_features.py   # NEW: Migration file
```

### Frontend Files to Create/Modify
```
frontend/
├── components/
│   ├── enhanced-sidebar.tsx              # ENHANCE: Add search, grouping
│   ├── thread-item.tsx                   # NEW: Thread item component
│   ├── thread-context-menu.tsx          # NEW: Context menu
│   ├── chat-search.tsx                   # NEW: Search component
│   └── ui/
│       └── context-menu.tsx              # NEW: Reusable context menu
├── hooks/
│   └── use-threads.ts                    # ENHANCE: Add delete, archive, search
└── lib/
    └── date-utils.ts                     # NEW: Date formatting utilities
```

---

## Testing Checklist

### Backend Tests
- [ ] Thread deletion removes thread and messages
- [ ] Thread search returns relevant results
- [ ] Auto title generation works
- [ ] Thread preview updates on new message
- [ ] Archived threads excluded from main list
- [ ] Pinned threads appear first

### Frontend Tests
- [ ] Sidebar displays threads correctly
- [ ] Search filters threads
- [ ] Delete thread removes from list
- [ ] Rename thread updates title
- [ ] Date grouping works correctly
- [ ] Real-time updates work

### Integration Tests
- [ ] Creating thread updates sidebar
- [ ] Sending message updates thread preview
- [ ] Navigation between threads works
- [ ] All CRUD operations work

---

## Performance Considerations

1. **Pagination**:
   - Limit threads loaded initially (50)
   - Load more on scroll
   - Virtual scrolling for large lists

2. **Caching**:
   - Cache thread list in frontend
   - Use React Query or SWR for cache management
   - Invalidate cache on mutations

3. **Search Optimization**:
   - Debounce search input (300ms)
   - Use PostgreSQL full-text search
   - Limit search results (50 max)

4. **Database Indexes**:
   - Index on `(org_id, updated_at)` for list query
   - Full-text search index for search
   - Index on `archived` for filtering

---

## Security Considerations

1. **Authorization**:
   - Verify user can only access their org's threads
   - Check permissions on all thread operations
   - Use existing RLS (Row Level Security) if available

2. **Input Validation**:
   - Validate thread titles (length, content)
   - Sanitize search queries
   - Rate limit search endpoints

3. **Soft Delete** (Recommended):
   - Consider soft delete instead of hard delete
   - Allows recovery and audit trail
   - Filter deleted threads from queries

---

## Future Enhancements (Post-MVP)

1. **Folders/Categories**:
   - Organize threads into folders
   - Drag-and-drop to organize
   - Tags/labels for threads

2. **Export/Share**:
   - Export conversation as markdown/PDF
   - Share thread via link
   - Copy conversation content

3. **Advanced Search**:
   - Search within messages
   - Filter by date range
   - Filter by model/provider
   - Search in attachments

4. **Thread Templates**:
   - Save thread as template
   - Start new thread from template

5. **Collaboration**:
   - Share threads with team members
   - Thread comments/notes

---

## Estimated Implementation Time

- **Phase 1 (Backend)**: 1-2 days
- **Phase 2 (Database)**: 0.5 day
- **Phase 3 (Frontend Core)**: 2-3 days
- **Phase 4 (UI Polish)**: 1-2 days
- **Testing & Bug Fixes**: 1-2 days

**Total**: 5-10 days for complete implementation

---

## Quick Start Guide

1. **Start with Backend**:
   - Add DELETE endpoint
   - Add auto title generation
   - Add search endpoint

2. **Then Frontend**:
   - Enhance sidebar with search
   - Add thread actions menu
   - Implement delete functionality

3. **Polish**:
   - Date formatting
   - Empty states
   - Loading states

4. **Test**:
   - Test all CRUD operations
   - Test search functionality
   - Test real-time updates

---

## Questions or Issues?

Refer to:
- Current implementation in `backend/app/api/threads.py`
- Sidebar component in `frontend/components/enhanced-sidebar.tsx`
- Thread model in `backend/app/models/thread.py`

This guide provides a comprehensive roadmap. Start with Phase 1 and work through sequentially, testing as you go.

