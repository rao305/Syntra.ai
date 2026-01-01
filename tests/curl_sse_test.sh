#!/bin/bash
#
# SYNTRA Real-World SSE Test (curl-based)
#
# Tests the collaborate streaming endpoint using curl
# Works without Node.js dependencies
#
# Usage: ./tests/curl_sse_test.sh [prompt]
#

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
ORG_ID="${ORG_ID:-test-org}"
DEFAULT_PROMPT="Give me a fault-tolerant architecture for a multi-LLM reasoning system that scales to 1M users."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

PROMPT="${1:-$DEFAULT_PROMPT}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  SYNTRA Real-World SSE Test (curl)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Create a new thread
echo -e "${YELLOW}1. Creating test thread...${NC}"
create_response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "X-Org-ID: $ORG_ID" \
    -d '{"title":"Real-World SSE Test"}' \
    "$BACKEND_URL/api/threads/")

THREAD_ID=$(echo "$create_response" | grep -o '"thread_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$THREAD_ID" ]; then
    echo -e "${RED}Failed to create thread!${NC}"
    echo "Response: $create_response"
    exit 1
fi

echo -e "   Thread ID: ${GREEN}$THREAD_ID${NC}"
echo ""

# Step 2: Show the prompt
echo -e "${YELLOW}2. Test Prompt:${NC}"
echo -e "   ${CYAN}${PROMPT:0:80}...${NC}"
echo ""

# Step 3: Run the SSE stream
echo -e "${YELLOW}3. Starting SSE collaboration stream...${NC}"
echo -e "   ${BLUE}(Watch for stage_start/stage_end events)${NC}"
echo ""

START_TIME=$(date +%s.%N)

# Prepare JSON body
JSON_BODY=$(cat <<EOF
{
    "message": "$PROMPT",
    "mode": "auto"
}
EOF
)

echo -e "${MAGENTA}═══ SSE Stream Output ═══${NC}"
echo ""

# Use curl to stream SSE events
curl -s -N \
    -X POST \
    -H "Content-Type: application/json" \
    -H "Accept: text/event-stream" \
    -H "X-Org-ID: $ORG_ID" \
    -d "$JSON_BODY" \
    "$BACKEND_URL/api/collaboration/$THREAD_ID/collaborate/stream" | while IFS= read -r line; do
    
    # Skip empty lines
    if [ -z "$line" ]; then
        continue
    fi
    
    # Parse SSE data lines
    if [[ "$line" == data:* ]]; then
        data="${line#data: }"
        
        # Extract event type
        event_type=$(echo "$data" | grep -o '"type":"[^"]*"' | cut -d'"' -f4)
        
        case "$event_type" in
            "stage_start")
                stage_id=$(echo "$data" | grep -o '"stage_id":"[^"]*"' | cut -d'"' -f4)
                echo -e "${MAGENTA}🔄 Stage START: ${stage_id}${NC}"
                ;;
            "stage_end")
                stage_id=$(echo "$data" | grep -o '"stage_id":"[^"]*"' | cut -d'"' -f4)
                echo -e "${GREEN}✓ Stage END: ${stage_id}${NC}"
                ;;
            "final_chunk")
                # Just print a dot for each chunk
                echo -n -e "${CYAN}.${NC}"
                ;;
            "done")
                echo ""
                echo -e "${GREEN}✅ SSE Stream Complete!${NC}"
                ;;
            "error")
                message=$(echo "$data" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
                echo -e "${RED}❌ Error: $message${NC}"
                ;;
            "pause_draft")
                echo -e "${YELLOW}⏸️  Manual mode pause - draft ready${NC}"
                ;;
            *)
                # Debug: show unknown events
                echo -e "${YELLOW}Unknown event: $event_type${NC}"
                ;;
        esac
    fi
done

END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)

echo ""
echo -e "${MAGENTA}═══════════════════════════${NC}"
echo ""
echo -e "${YELLOW}4. Results:${NC}"
echo -e "   Duration: ${GREEN}${DURATION}s${NC}"
echo -e "   Thread ID: ${CYAN}$THREAD_ID${NC}"
echo ""

# Step 4: Verify database
echo -e "${YELLOW}5. Fetching thread to verify DB save...${NC}"
thread_data=$(curl -s -H "X-Org-ID: $ORG_ID" "$BACKEND_URL/api/threads/$THREAD_ID")

message_count=$(echo "$thread_data" | grep -o '"messages":\[' | wc -l)
if echo "$thread_data" | grep -q '"role":"assistant"'; then
    echo -e "   ${GREEN}✓ Assistant message saved to database${NC}"
else
    echo -e "   ${RED}✗ No assistant message found${NC}"
fi

# Show collaborate metadata if present
if echo "$thread_data" | grep -q '"collaborate"'; then
    echo -e "   ${GREEN}✓ Collaborate metadata present${NC}"
    
    # Try to extract some metadata
    duration=$(echo "$thread_data" | grep -o '"duration_ms":[0-9]*' | head -1 | cut -d':' -f2)
    reviews=$(echo "$thread_data" | grep -o '"external_reviews_count":[0-9]*' | head -1 | cut -d':' -f2)
    
    if [ -n "$duration" ]; then
        echo -e "   Pipeline duration: ${CYAN}${duration}ms${NC}"
    fi
    if [ -n "$reviews" ]; then
        echo -e "   External reviews: ${CYAN}$reviews${NC}"
    fi
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Test complete!${NC}"
echo ""
echo "To verify database state, run:"
echo "  psql -d syntra -c \"SELECT meta->'collaborate' FROM messages WHERE thread_id='$THREAD_ID' AND role='assistant'\""
echo ""








