#!/bin/bash
# Final Phase-1 Sign-Off Procedure (Non-Interactive)
set -e

echo "=========================================="
echo "Phase-1 Final Sign-Off (Auto)"
echo "=========================================="
echo ""

# Step 1: Prep
echo "Step 1: Preparing test environment..."
source prep_ttft_test.sh
echo ""

# Check if backend is running
echo "Checking if backend is running..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
  echo "✅ Backend is running"
else
  echo "⚠️  Backend not detected at http://localhost:8000"
  echo "   Please start your backend server, then run this script again"
  echo "   Or run: cd backend && python main.py"
  exit 1
fi

# Step 2: Run suite
echo ""
echo "Step 2: Running TTFT verification suite..."
echo "=========================================="
./run_ttft_suite.sh | tee /tmp/ttft_results.txt

# Step 3: Extract and append results
echo ""
echo "Step 3: Appending results to PHASE1_GO_NO_GO.md..."
RESULTS=$(awk '/^• TTFT|^• Cancel latency|^• Queue wait/ {print}' /tmp/ttft_results.txt)

if [ -z "$RESULTS" ]; then
  echo "⚠️  Could not extract results. Please manually copy from above."
  echo ""
  echo "Look for lines starting with '• TTFT', '• Cancel latency', or '• Queue wait'"
else
  # Check if we should mark as PASS or FAIL
  if echo "$RESULTS" | grep -q "PASS\|OK"; then
    STATUS="PASS"
  else
    STATUS="PENDING"
  fi
  
  echo "" >> PHASE1_GO_NO_GO.md
  echo "## Phase-1 Final Verification — $STATUS" >> PHASE1_GO_NO_GO.md
  echo "" >> PHASE1_GO_NO_GO.md
  echo "$RESULTS" >> PHASE1_GO_NO_GO.md
  echo "" >> PHASE1_GO_NO_GO.md
  if [ "$STATUS" = "PASS" ]; then
    echo "**Decision**: ✅ Proceed to Phase-2" >> PHASE1_GO_NO_GO.md
  else
    echo "**Decision**: ⏳ Review results" >> PHASE1_GO_NO_GO.md
  fi
  echo ""
  echo "✅ Results appended to PHASE1_GO_NO_GO.md"
  echo ""
  echo "Results:"
  echo "$RESULTS"
fi

# Step 4: Restore production
echo ""
echo "Step 4: Restoring production settings..."
source restore_prod_settings.sh
echo ""
echo "⚠️  Please restart your backend server to apply production settings."
echo ""
echo "=========================================="
echo "Sign-Off Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review PHASE1_GO_NO_GO.md"
echo "2. Restart backend with production settings"
echo "3. Run production cutover checklist (see PRODUCTION_CUTOVER_CHECKLIST.md)"


