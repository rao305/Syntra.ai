# Database Migration Guide

## How to Run Migrations

### Important: Always Activate Virtual Environment First!

Alembic is installed in the virtual environment, so you need to activate it before running migration commands.

### Steps:

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```
   
   On Windows:
   ```bash
   venv\Scripts\activate
   ```

3. **Run migration commands:**
   ```bash
   # Check current migration version
   alembic current
   
   # Upgrade to latest migration
   alembic upgrade head
   
   # Create a new migration
   alembic revision -m "description of changes"
   
   # Downgrade one version
   alembic downgrade -1
   
   # View migration history
   alembic history
   ```

### Quick Reference Commands

```bash
# One-liner to activate venv and run migration
cd backend && source venv/bin/activate && alembic upgrade head

# Check status
cd backend && source venv/bin/activate && alembic current

# View all migrations
cd backend && source venv/bin/activate && alembic history
```

## Current Migration Status

✅ **Migration 010 Applied** - Add archiving support to threads
- Added `archived` column (Boolean, default False)
- Added `archived_at` column (DateTime, nullable)
- Created indexes for performance

## Troubleshooting

### "command not found: alembic"
- **Solution:** Activate virtual environment first: `source venv/bin/activate`

### "No such file or directory: venv"
- **Solution:** Create virtual environment:
  ```bash
  cd backend
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```

### Migration conflicts
- Check current version: `alembic current`
- View history: `alembic history`
- Check for conflicts in migration files

## Migration Files Location

All migration files are in: `backend/migrations/versions/`

## For Future Migrations

When creating new migrations:

```bash
cd backend
source venv/bin/activate
alembic revision -m "your migration description"
```

This will create a new migration file in `backend/migrations/versions/` that you can edit.

