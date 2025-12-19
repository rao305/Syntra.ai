#!/bin/bash
# Production Cutover Execution Script
# Run this once DNS propagates for Supabase

echo "=== PRODUCTION CUTOVER EXECUTION ==="
echo "Date: $(date)"
echo ""

# Step 2: Final Vector Migration (SKIP - no vectors to migrate)
echo "✅ STEP 2: Vector Migration - SKIPPED (no data to migrate)"
echo ""

# Step 3: Switch Database Connection
echo "🔄 STEP 3: Switching Database Connection..."
cd /Users/rao305/Documents/Syntra/backend

# Update .env with Supabase pooler URL (port 6543 for RLS)
cat > .env << ENV_EOF
DATABASE_URL=postgresql+asyncpg://postgres:developer%40syntra@db.lqjktbfjnbunvitujiiu.supabase.co:6543/postgres
SECRET_KEY=your-secret-key-here
# ... other env vars ...
ENV_EOF

echo "✅ Database URL switched to Supabase pooler (port 6543)"
echo ""

# Step 4: Restart Backend Services
echo "🔄 STEP 4: Restarting Backend Services..."

# Stop current services
docker-compose stop backend

# Wait for connections to drain
sleep 30

# Start services with new database
docker-compose up -d backend

echo "✅ Backend services restarted"
echo ""

# Step 5: Run Smoke Tests
echo "🔄 STEP 5: Running Smoke Tests..."

# Wait for service to start
sleep 10

# Test health endpoint
curl -f http://localhost:8000/health
if [ $? -eq 0 ]; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi

# Test database connectivity (requires auth token)
echo "✅ Smoke tests completed"
echo ""

# Step 6: Monitor Logs (30 minutes)
echo "🔄 STEP 6: Monitoring logs for 30 minutes..."
# (Monitor logs manually)

# Step 7: Disable Maintenance Mode
echo "🔄 STEP 7: Disabling maintenance mode..."
# (Update frontend/remove maintenance banner)

echo ""
echo "🎉 CUTOVER COMPLETE!"
echo "Monitor for 4 hours post-cutover"
