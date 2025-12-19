#!/bin/bash
# Pre-cutover readiness verification

echo "🔍 PRE-CUTOVER READINESS VERIFICATION"
echo "======================================"
echo ""

# Check 1: DNS Resolution
echo "1. DNS Resolution Check:"
if nslookup db.lqjktbfjnbunvitujiiu.supabase.co >/dev/null 2>&1; then
    echo "   ✅ DNS resolved"
else
    echo "   ❌ DNS not resolving yet"
fi
echo ""

# Check 2: Dependencies
echo "2. Dependencies Check:"
if python3 -c "import supabase" >/dev/null 2>&1; then
    echo "   ✅ Supabase library installed"
else
    echo "   ❌ Supabase library missing"
fi

if python3 -c "import psycopg2" >/dev/null 2>&1; then
    echo "   ✅ psycopg2 installed"
else
    echo "   ❌ psycopg2 missing"
fi
echo ""

# Check 3: Code Syntax
echo "3. Code Syntax Check:"
cd /Users/rao305/Documents/Syntra/backend
if python3 -c "import app.main" >/dev/null 2>&1; then
    echo "   ✅ Main app imports successfully"
else
    echo "   ❌ Main app import failed"
fi
echo ""

# Check 4: Git Status
echo "4. Git Status Check:"
if [[ -z $(git status --porcelain) ]]; then
    echo "   ✅ Git working directory clean"
else
    echo "   ❌ Uncommitted changes exist"
fi
echo ""

# Check 5: Docker Services
echo "5. Docker Services Check:"
if docker ps | grep -q syntra-postgres; then
    echo "   ✅ PostgreSQL container running"
else
    echo "   ❌ PostgreSQL container not running"
fi

if docker ps | grep -q syntra-qdrant; then
    echo "   ✅ Qdrant container running"
else
    echo "   ❌ Qdrant container not running"
fi
echo ""

# Check 6: Backup Verification
echo "6. Backup Verification:"
if [[ -f "/Users/rao305/Documents/Syntra/postgres_backup_20251219_165618.sql" ]]; then
    echo "   ✅ PostgreSQL backup exists ($(du -h postgres_backup_20251219_165618.sql | cut -f1))"
else
    echo "   ❌ PostgreSQL backup missing"
fi
echo ""

echo "🎯 READINESS SUMMARY:"
echo "- Run this script periodically until DNS resolves"
echo "- Once all checks pass, execute: bash cutover_execution.sh"
echo "- Expected cutover time: 4-6 hours maintenance window"
