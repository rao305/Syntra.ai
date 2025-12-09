# Your Chats Feature - Quick Reference

## What You Need to Implement

### ✅ Already Have
- Thread storage (PostgreSQL)
- Basic sidebar showing threads
- Thread listing API endpoint
- Message storage linked to threads

### 🔨 What to Build

#### Backend (2-3 days)
1. **Delete Thread** - `DELETE /api/threads/{thread_id}`
2. **Search Threads** - `GET /api/threads/search?q={query}`
3. **Auto-generate Titles** - When first message sent
4. **Update Preview** - Update `last_message_preview` on new message
5. **Archive Threads** - Add `archived` column

#### Frontend (3-4 days)
1. **Enhanced Sidebar**:
   - Search bar at top
   - Group by date (Today, Yesterday, etc.)
   - Thread actions menu (rename, delete, archive)
   - Pinned threads section

2. **Thread Management**:
   - Delete confirmation
   - Inline title editing
   - Context menu (right-click)

3. **Real-time Updates**:
   - Refresh sidebar when thread created
   - Update preview when message sent

## Key Files to Modify

### Backend
- `backend/app/api/threads.py` - Add endpoints
- `backend/app/models/thread.py` - Add `archived` field
- `backend/migrations/` - Create migration

### Frontend
- `frontend/components/enhanced-sidebar.tsx` - Enhance UI
- `frontend/hooks/use-threads.ts` - Add delete/archive/search
- `frontend/app/conversations/page.tsx` - Real-time updates

## Database Changes

```sql
-- Add archiving
ALTER TABLE threads ADD COLUMN archived BOOLEAN DEFAULT FALSE;

-- Add search index
CREATE INDEX idx_threads_fulltext_search 
ON threads USING gin(to_tsvector('english', 
  coalesce(title, '') || ' ' || coalesce(last_message_preview, '')
));
```

## API Endpoints to Add

```
DELETE /api/threads/{thread_id}           # Delete thread
GET    /api/threads/search?q={query}      # Search threads
PATCH  /api/threads/{thread_id}/archive   # Archive/unarchive
```

## UI Components to Create

1. `ThreadItem` - Individual thread in sidebar
2. `ThreadContextMenu` - Actions menu
3. `ChatSearch` - Search input component

## Implementation Order

1. ✅ Backend DELETE endpoint
2. ✅ Auto title generation
3. ✅ Update preview on message
4. ✅ Frontend delete functionality
5. ✅ Enhanced sidebar UI
6. ✅ Search functionality
7. ✅ Polish & testing

## Estimated Time: 5-10 days

See `YOUR_CHATS_IMPLEMENTATION_GUIDE.md` for full details.

