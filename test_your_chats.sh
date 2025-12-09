#!/bin/bash

# Quick test script for Your Chats feature
# Usage: ./test_your_chats.sh

ORG_ID="org_demo"
BASE_URL="http://localhost:8000/api"

echo "🧪 Testing Your Chats Feature"
echo "=============================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Backend Health Check
echo "1️⃣ Testing: Backend Health"
if curl -s -f -X GET "http://localhost:8000/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend is running${NC}"
else
    echo -e "${RED}❌ Backend is not running. Start it with: cd backend && source venv/bin/activate && python main.py${NC}"
    exit 1
fi
echo ""

# Test 2: List Threads
echo "2️⃣ Testing: List Threads (Non-Archived)"
RESPONSE=$(curl -s -X GET "${BASE_URL}/threads?limit=5" -H "x-org-id: ${ORG_ID}")
if [ $? -eq 0 ]; then
    COUNT=$(echo "$RESPONSE" | grep -o '"id"' | wc -l | tr -d ' ')
    if [ "$COUNT" -gt 0 ]; then
        echo -e "${GREEN}✅ Found ${COUNT} thread(s)${NC}"
        echo "Sample thread:"
        echo "$RESPONSE" | head -c 200
        echo "..."
    else
        echo -e "${YELLOW}⚠️  No threads found (this is ok if no conversations exist yet)${NC}"
    fi
else
    echo -e "${RED}❌ Failed to list threads${NC}"
fi
echo ""

# Test 3: Search Threads
echo "3️⃣ Testing: Search Threads"
SEARCH_RESPONSE=$(curl -s -X GET "${BASE_URL}/threads/search?q=test&limit=5" -H "x-org-id: ${ORG_ID}")
if [ $? -eq 0 ]; then
    if echo "$SEARCH_RESPONSE" | grep -q '"id"'; then
        echo -e "${GREEN}✅ Search endpoint working${NC}"
    else
        echo -e "${YELLOW}⚠️  Search returned no results (ok if no matching threads)${NC}"
    fi
else
    echo -e "${RED}❌ Search endpoint failed${NC}"
fi
echo ""

# Test 4: Check Database Schema (archived column exists)
echo "4️⃣ Testing: Database Schema (Migration Applied)"
echo "Checking if migration 010 is applied..."
cd backend
source venv/bin/activate
MIGRATION=$(alembic current 2>&1 | grep -o "010" | head -1)
if [ "$MIGRATION" = "010" ]; then
    echo -e "${GREEN}✅ Migration 010 is applied (archived fields exist)${NC}"
else
    echo -e "${RED}❌ Migration 010 not applied. Run: alembic upgrade head${NC}"
fi
deactivate
cd ..
echo ""

echo "=============================="
echo -e "${GREEN}✅ Basic backend tests complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Open http://localhost:3000/conversations in browser"
echo "2. Test frontend features manually"
echo "3. Check browser console for errors"

