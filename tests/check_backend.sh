#!/bin/bash
#
# SYNTRA Backend Health Check Script
# 
# Verifies that all components are ready for real-world testing
#
# Usage: ./tests/check_backend.sh [backend_url]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BACKEND_URL="${1:-http://localhost:8000}"
ORG_ID="${ORG_ID:-test-org}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  SYNTRA Backend Health Check${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

check_passed=0
check_failed=0

# Function to check endpoint
check_endpoint() {
    local name="$1"
    local url="$2"
    local method="${3:-GET}"
    local body="$4"
    local expected_status="${5:-200}"
    
    echo -n "  Checking $name... "
    
    if [ "$method" == "POST" ] && [ -n "$body" ]; then
        response=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
            -H "Content-Type: application/json" \
            -H "X-Org-ID: $ORG_ID" \
            -d "$body" \
            "$url" 2>/dev/null)
    else
        response=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "X-Org-ID: $ORG_ID" \
            "$url" 2>/dev/null)
    fi
    
    if [ "$response" == "$expected_status" ]; then
        echo -e "${GREEN}✓ OK (HTTP $response)${NC}"
        ((check_passed++))
        return 0
    else
        echo -e "${RED}✗ FAILED (HTTP $response, expected $expected_status)${NC}"
        ((check_failed++))
        return 1
    fi
}

# 1. Backend Health
echo -e "${YELLOW}1. Core Backend Health${NC}"
check_endpoint "Health endpoint" "$BACKEND_URL/health"
check_endpoint "OpenAPI docs" "$BACKEND_URL/docs"

# 2. Thread API
echo ""
echo -e "${YELLOW}2. Thread API${NC}"
check_endpoint "List threads" "$BACKEND_URL/api/threads/"

# 3. Collaboration Endpoints
echo ""
echo -e "${YELLOW}3. Collaboration Endpoints${NC}"
check_endpoint "Available models" "$BACKEND_URL/api/dynamic-collaborate/available-models"
check_endpoint "Model capabilities" "$BACKEND_URL/api/dynamic-collaborate/capabilities"

# 4. Check if DB is connected (by listing threads)
echo ""
echo -e "${YELLOW}4. Database Connection${NC}"
thread_response=$(curl -s -H "X-Org-ID: $ORG_ID" "$BACKEND_URL/api/threads/" 2>/dev/null)
if echo "$thread_response" | grep -q "\[" 2>/dev/null; then
    echo -e "  Database connection: ${GREEN}✓ Connected${NC}"
    ((check_passed++))
else
    echo -e "  Database connection: ${RED}✗ Failed${NC}"
    ((check_failed++))
fi

# 5. Provider API Keys Check
echo ""
echo -e "${YELLOW}5. Provider API Keys${NC}"
models_response=$(curl -s -H "X-Org-ID: $ORG_ID" "$BACKEND_URL/api/dynamic-collaborate/available-models" 2>/dev/null)

# Check each provider
providers=("openai" "gemini" "perplexity" "kimi" "openrouter")
for provider in "${providers[@]}"; do
    if echo "$models_response" | grep -qi "\"provider\":.*\"$provider\"" 2>/dev/null; then
        echo -e "  $provider: ${GREEN}✓ Configured${NC}"
    else
        echo -e "  $provider: ${YELLOW}⚠ Not configured${NC}"
    fi
done

# 6. Test Thread Creation
echo ""
echo -e "${YELLOW}6. Thread Operations${NC}"
create_response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "X-Org-ID: $ORG_ID" \
    -d '{"title":"Health Check Test Thread"}' \
    "$BACKEND_URL/api/threads/" 2>/dev/null)

if echo "$create_response" | grep -q "thread_id" 2>/dev/null; then
    echo -e "  Thread creation: ${GREEN}✓ Working${NC}"
    ((check_passed++))
    
    # Extract thread_id for cleanup
    thread_id=$(echo "$create_response" | grep -o '"thread_id":"[^"]*"' | cut -d'"' -f4)
    
    # Delete the test thread
    delete_response=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
        -H "X-Org-ID: $ORG_ID" \
        "$BACKEND_URL/api/threads/$thread_id" 2>/dev/null)
    
    if [ "$delete_response" == "200" ]; then
        echo -e "  Thread deletion: ${GREEN}✓ Working${NC}"
        ((check_passed++))
    else
        echo -e "  Thread deletion: ${RED}✗ Failed${NC}"
        ((check_failed++))
    fi
else
    echo -e "  Thread creation: ${RED}✗ Failed${NC}"
    ((check_failed++))
fi

# 7. SSE Endpoint Accessibility
echo ""
echo -e "${YELLOW}7. SSE Streaming Endpoints${NC}"

# Check if collaborate stream endpoint exists (OPTIONS check)
collaborate_check=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS \
    "$BACKEND_URL/api/collaboration/test-thread/collaborate/stream" 2>/dev/null)

if [ "$collaborate_check" != "000" ]; then
    echo -e "  Collaborate stream: ${GREEN}✓ Endpoint exists${NC}"
    ((check_passed++))
else
    echo -e "  Collaborate stream: ${YELLOW}⚠ May not be accessible${NC}"
fi

# Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Passed: ${GREEN}$check_passed${NC}"
echo -e "  Failed: ${RED}$check_failed${NC}"
echo ""

if [ $check_failed -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Backend is ready for testing.${NC}"
    echo ""
    echo "Run the real-world tests:"
    echo "  node tests/real_world_sse_tests.mjs"
    echo ""
    exit 0
else
    echo -e "${YELLOW}⚠️  Some checks failed. Please fix the issues above before testing.${NC}"
    echo ""
    exit 1
fi








