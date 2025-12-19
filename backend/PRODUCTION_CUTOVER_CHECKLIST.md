# Day 8: Production Cutover Checklist

## 🎯 Cutover Timeline: 4-6 Hour Maintenance Window

**Estimated Schedule**: 8:00 AM - 2:00 PM UTC

---

## ✅ PRE-CUTOVER VALIDATION (Day 7)

### Code Quality
- [ ] All syntax verified with `py_compile`
- [ ] All imports verified
- [ ] Test suite created and ready
- [ ] No merge conflicts
- [ ] All changes committed to git

### Data Validation
- [ ] Database backups taken
- [ ] Vector count verified in Qdrant
- [ ] Memory fragment count verified
- [ ] Attachment BLOB count verified

### Infrastructure
- [ ] Supabase project fully provisioned
- [ ] pgvector extension enabled
- [ ] Storage bucket created with RLS policies
- [ ] Connection pooler URL working
- [ ] SSL certificates valid

### Team Communication
- [ ] Stakeholders notified of maintenance window
- [ ] Support team on standby
- [ ] Rollback plan documented
- [ ] Escalation contacts confirmed

---

## 🚀 CUTOVER STEPS (8:00 AM - 2:00 PM)

### STEP 1: Enable Maintenance Mode (8:00 AM)

**Duration**: 5 minutes

```bash
# Option A: If using a maintenance flag environment variable
export MAINTENANCE_MODE=true

# Option B: If using a maintenance endpoint
curl -X POST https://api.yourdomain.com/admin/maintenance/enable \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Option C: Update frontend to show maintenance banner
# Edit frontend config to redirect to /maintenance page
```

**Verification**:
```bash
curl https://api.yourdomain.com/health
# Should show maintenance status or unavailable
```

**User Communication**:
- [ ] Send notification to users about maintenance window
- [ ] Monitor support channel for questions

---

### STEP 2: Final Data Sync (8:15 AM)

**Duration**: 15-30 minutes (depends on data volume)

#### 2a: Run Final Vector Migration

```bash
cd /Users/rao305/Documents/Syntra/backend

export DATABASE_URL="postgresql+asyncpg://postgres:developer%40syntra@db.lqjktbfjnbunvitujiiu.supabase.co:5432/postgres"

# Run vector migration from Qdrant to pgvector
/Users/rao305/Documents/Syntra/backend/venv/bin/python scripts/migrate_vectors_to_pgvector.py

# Expected output:
# ✅ Migration complete: X/Y vectors migrated
# Success Rate: 95%+
```

**Verification**:
```bash
# Count vectors in Supabase
psql $SUPABASE_DB_URL -c \
  "SELECT COUNT(*) as total_vectors FROM memory_fragments WHERE embedding IS NOT NULL;"

# Count vectors still in Qdrant
# qdrant_cli collection info dac_memory | grep points_count
```

**Expected**:
- Vector counts should match (or be very close)
- Success rate should be > 95%
- Duration should be < 30 minutes

#### 2b: Verify Data Consistency

```bash
# Check for any inconsistencies
psql $SUPABASE_DB_URL << EOF
-- Compare vector counts
SELECT
  COUNT(*) as total_fragments,
  COUNT(embedding) as with_vectors,
  COUNT(vector_id) as with_qdrant_id,
  COUNT(embedding) - COUNT(vector_id) as vectors_only
FROM memory_fragments;

-- Check for any NULL file_data without storage_path
SELECT COUNT(*) as problematic_attachments
FROM attachments
WHERE file_data IS NULL AND storage_path IS NULL;

-- Verify org isolation still working
SELECT COUNT(DISTINCT org_id) as org_count FROM memory_fragments;
EOF
```

---

### STEP 3: Switch Database Connection (9:00 AM)

**Duration**: 5 minutes

#### 3a: Update Environment Variables

**File**: `/backend/.env` (production)

```bash
# BEFORE (old database)
# DATABASE_URL=postgresql+asyncpg://old.database.com/...

# AFTER (Supabase transaction pooler - REQUIRED for RLS)
DATABASE_URL=postgresql+asyncpg://postgres:developer%40syntra@db.lqjktbfjnbunvitujiiu.supabase.co:6543/postgres

# Can optionally remove old Qdrant config (not needed anymore)
# QDRANT_URL=
# QDRANT_API_KEY=
```

**⚠️ CRITICAL**: Use port **6543** (transaction pooler), NOT 5432 (session pooler)
- Port 6543: Supports `SET LOCAL` for RLS context ✅
- Port 5432: Loses context between requests ❌

#### 3b: Verify New Connection String

```bash
# Test new connection string
psql postgresql://postgres:developer%40syntra@db.lqjktbfjnbunvitujiiu.supabase.co:6543/postgres << EOF
SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public';
\q
EOF
```

---

### STEP 4: Restart Backend Services (9:15 AM)

**Duration**: 10 minutes (includes boot time)

#### 4a: Stop Current Services

```bash
# Option A: Docker Compose
cd /Users/rao305/Documents/Syntra
docker-compose stop backend

# Option B: Systemd
sudo systemctl stop syntra-backend

# Option C: PM2
pm2 stop syntra-backend

# Option D: Kubernetes
kubectl rollout restart deployment/syntra-backend -n production
```

#### 4b: Clear Connection Pools (Important!)

```bash
# Wait 30 seconds for connections to drain
sleep 30

# If using Docker, optionally prune old containers
docker system prune -f
```

#### 4c: Start New Services

```bash
# Option A: Docker Compose
docker-compose up -d backend

# Option B: Systemd
sudo systemctl start syntra-backend

# Option C: PM2
pm2 start syntra-backend

# Option D: Kubernetes
kubectl rollout status deployment/syntra-backend -n production
```

**Verification**:
```bash
# Wait for service to be ready
sleep 10

# Check service is running
curl http://localhost:8000/health
# Should return: {"status": "healthy"}
```

---

### STEP 5: Run Smoke Tests (9:30 AM)

**Duration**: 10 minutes

Run these tests to verify critical functionality:

#### 5a: Health Check

```bash
echo "Testing health endpoint..."
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

#### 5b: Database Connectivity

```bash
echo "Testing database connectivity..."
/Users/rao305/Documents/Syntra/backend/venv/bin/python << 'EOF'
import asyncio
from app.database import engine
from sqlalchemy import text

async def test():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM threads"))
        count = result.scalar()
        print(f"✅ Database connected. Thread count: {count}")

asyncio.run(test())
EOF
```

#### 5c: RLS Testing

```bash
echo "Testing RLS isolation..."
/Users/rao305/Documents/Syntra/backend/venv/bin/python << 'EOF'
import asyncio
from app.database import AsyncSessionLocal
from app.security import set_rls_context
from app.models.thread import Thread
from sqlalchemy import select

async def test():
    async with AsyncSessionLocal() as db:
        # Set context for org_test
        await set_rls_context(db, "org_test", "user_test")

        # Try to query
        result = await db.execute(select(Thread))
        threads = result.scalars().all()
        print(f"✅ RLS working. Found {len(threads)} threads for org_test")

asyncio.run(test())
EOF
```

#### 5d: Vector Search Test

```bash
echo "Testing vector search (pgvector)..."
/Users/rao305/Documents/Syntra/backend/venv/bin/python << 'EOF'
import asyncio
from app.database import AsyncSessionLocal
from app.security import set_rls_context
from sqlalchemy import text, select
from app.models.memory import MemoryFragment

async def test():
    async with AsyncSessionLocal() as db:
        # Set RLS context
        await set_rls_context(db, "org_demo", "user_demo")

        # Check if we have any vectors
        result = await db.execute(
            select(MemoryFragment).where(MemoryFragment.embedding.isnot(None))
        )
        fragments = result.scalars().all()

        if fragments:
            print(f"✅ Vector search ready. {len(fragments)} fragments with embeddings")
        else:
            print("⚠️  No vectors yet (OK if first deploy)")

asyncio.run(test())
EOF
```

#### 5e: Storage Access Test

```bash
echo "Testing file storage access..."
/Users/rao305/Documents/Syntra/backend/venv/bin/python << 'EOF'
try:
    from app.services.storage_service import storage_service
    print("✅ Storage service initialized")
except Exception as e:
    print(f"❌ Storage service error: {e}")
EOF
```

#### 5f: API Endpoint Test (if frontend available)

```bash
echo "Testing API endpoints..."
curl -X GET http://localhost:8000/api/threads \
  -H "x-org-id: org_demo" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  || echo "⚠️  Endpoint test skipped (auth required)"
```

**Summary**:
```bash
echo ""
echo "=========================================="
echo "✅ SMOKE TESTS COMPLETED"
echo "=========================================="
echo "If all tests passed above, proceed to step 6"
```

---

### STEP 6: Monitor Logs (9:45 AM - 10:15 AM)

**Duration**: 30 minutes

**Watch for errors**:

```bash
# Option A: Docker Compose
docker-compose logs -f backend | grep -E "(ERROR|WARNING|CRITICAL)" &
TAIL_PID=$!

# Option B: Systemd
journalctl -u syntra-backend -f | grep -E "(ERROR|WARNING|CRITICAL)" &
TAIL_PID=$!

# Option C: PM2
pm2 logs syntra-backend | grep -E "(ERROR|WARNING|CRITICAL)" &
TAIL_PID=$!

# Monitor for 30 minutes
sleep 1800

# Stop monitoring
kill $TAIL_PID
```

**What to look for**:
- ❌ Database connection errors
- ❌ RLS context errors
- ❌ Vector search timeouts
- ❌ Storage access errors
- ⚠️ High latency spikes
- ⚠️ Memory usage growth

**If errors found**:
- Note the exact error message
- Check Step 7: Rollback if needed
- Do NOT disable maintenance mode yet

---

### STEP 7: Disable Maintenance Mode (10:30 AM)

**Only if all smoke tests passed!**

```bash
# Option A: Environment variable
unset MAINTENANCE_MODE

# Option B: API endpoint
curl -X POST https://api.yourdomain.com/admin/maintenance/disable \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Option C: Frontend config
# Remove maintenance redirect from frontend
```

**Verification**:
```bash
curl https://api.yourdomain.com/health
# Should return: {"status": "healthy"} (not maintenance message)
```

**User Communication**:
- [ ] Send "maintenance complete" notification
- [ ] Confirm service is fully operational
- [ ] Thank users for patience

---

## 🔄 ROLLBACK PROCEDURE (If needed)

**Triggers for rollback**:
- Error rate > 5%
- RLS data leakage detected
- Database connection failures
- Critical feature broken
- Vector search completely broken

### Quick Rollback (< 10 minutes)

```bash
# 1. Enable maintenance mode immediately
export MAINTENANCE_MODE=true

# 2. Switch back to old database URL
# Edit .env and revert DATABASE_URL

# 3. Restart services
docker-compose restart backend  # or equivalent

# 4. Verify old system working
curl http://localhost:8000/health

# 5. Investigate in parallel
# Check logs, contact team, etc.
```

### Full Rollback Steps

```bash
# 1. Restore old DATABASE_URL in .env
DATABASE_URL=postgresql+asyncpg://old-postgres:5432/dac

# 2. Restart services
systemctl restart syntra-backend

# 3. Verify health
curl http://localhost:8000/health

# 4. Keep Supabase data intact (for investigation)
# Don't delete anything yet

# 5. Alert team
# Send incident alert, schedule post-mortem
```

---

## 📊 POST-CUTOVER MONITORING (10:30 AM - 2:00 PM)

**First 4 hours critical**:

### Every 15 Minutes:

```bash
# Check error rate
curl https://api.yourdomain.com/health
# Should be 200 OK

# Check key metrics
# - Database query latency
# - Vector search latency
# - Storage access latency
# - Error count
# - Memory usage
```

### Check Supabase Dashboard:

1. **Database**
   - Go to Logs → check for errors
   - Query Performance → watch for slow queries
   - Connection count → should be reasonable

2. **Storage**
   - Check upload/download activity
   - Monitor storage usage
   - Check for access errors

3. **Analytics**
   - Monitor API request volume
   - Track error rates
   - Check response times

### Success Criteria:

- ✅ Error rate < 1%
- ✅ No RLS data leaks
- ✅ Vector search latency < 100ms
- ✅ Storage operations succeeding
- ✅ Database stable
- ✅ User reports positive

---

## 📋 FINAL CHECKLIST

### Pre-Cutover (Day 7)
- [ ] All code reviewed
- [ ] Syntax verified
- [ ] Database backups taken
- [ ] Supabase project ready
- [ ] Team notified

### During Cutover (8:00 AM - 2:00 PM)
- [ ] Maintenance mode enabled
- [ ] Vector migration completed successfully
- [ ] Database URL switched to Supabase pooler
- [ ] Services restarted
- [ ] All smoke tests passed
- [ ] Logs monitored for 30 minutes
- [ ] Maintenance mode disabled
- [ ] Users notified of completion

### Post-Cutover (Week 1)
- [ ] Monitoring continued for 24 hours
- [ ] No critical issues found
- [ ] Error rates < 1%
- [ ] BLOB migration script run (during low traffic)
- [ ] Old infrastructure decommissioned (after 7 days stable)

---

## 🆘 SUPPORT CONTACTS

**If something goes wrong**:

1. **Immediate**: Enable maintenance mode
2. **Call**: On-call team (see contact list)
3. **Chat**: Team Slack #incidents
4. **Escalation**: CTO or Engineering Lead

**Supabase Support**:
- Dashboard: https://supabase.com/dashboard
- Status: https://status.supabase.com
- Docs: https://supabase.com/docs

---

## ✅ SIGN-OFF

Once completed, fill in below:

```
Date: _________________
Time: _________________
Lead: _________________
Status: [ ] SUCCESS [ ] ROLLBACK

Issues encountered: _________________________________________________

Post-cutover notes: _________________________________________________
```

---

**Good luck with the cutover! You've got this! 🚀**
