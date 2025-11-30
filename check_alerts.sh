#!/bin/bash
# Quick alert check - monitors key metrics
set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
METRICS=$(curl -s "${BASE_URL}/api/metrics/performance?last_n=100")

TTFT_P95=$(echo "$METRICS" | jq -r '.ttft_ms.p95 // "N/A"')
ERROR_RATE=$(echo "$METRICS" | jq -r '.error_rate // "N/A"')
QUEUE_WAIT_P95=$(echo "$METRICS" | jq -r '.queue_wait_ms.p95 // "N/A"')
LEADERS=$(echo "$METRICS" | jq -r '.coalesce.leaders // 0')
FOLLOWERS=$(echo "$METRICS" | jq -r '.coalesce.followers // 0')

echo "=== Alert Check ==="
echo ""

ALERTS=0

# TTFT check
if [ "$TTFT_P95" != "N/A" ] && awk "BEGIN {exit !($TTFT_P95 > 1500)}" 2>/dev/null; then
  echo "⚠️  TTFT regression: p95=${TTFT_P95}ms > 1500ms"
  ALERTS=$((ALERTS + 1))
else
  echo "✅ TTFT p95: ${TTFT_P95}ms"
fi

# Error rate check
if [ "$ERROR_RATE" != "N/A" ] && awk "BEGIN {exit !($ERROR_RATE > 0.01)}" 2>/dev/null; then
  echo "⚠️  Error rate high: ${ERROR_RATE} > 1%"
  ALERTS=$((ALERTS + 1))
else
  echo "✅ Error rate: ${ERROR_RATE}"
fi

# Queue wait check
if [ "$QUEUE_WAIT_P95" != "N/A" ] && awk "BEGIN {exit !($QUEUE_WAIT_P95 > 1000)}" 2>/dev/null; then
  echo "⚠️  Queue saturation: p95=${QUEUE_WAIT_P95}ms > 1000ms"
  ALERTS=$((ALERTS + 1))
else
  echo "✅ Queue wait p95: ${QUEUE_WAIT_P95}ms"
fi

# Coalescing check
if [ "$LEADERS" -gt 0 ]; then
  RATIO=$(awk "BEGIN {printf \"%.1f\", $FOLLOWERS/$LEADERS}")
  if awk "BEGIN {exit !($RATIO < 10)}" 2>/dev/null; then
    echo "⚠️  Coalescing efficiency low: ratio=${RATIO} (followers/leaders)"
    ALERTS=$((ALERTS + 1))
  else
    echo "✅ Coalescing ratio: ${RATIO} (followers/leaders)"
  fi
else
  echo "ℹ️  No coalescing data yet"
fi

echo ""

if [ $ALERTS -eq 0 ]; then
  echo "✅ All checks passed"
  exit 0
else
  echo "⚠️  ${ALERTS} alert(s) detected"
  echo ""
  echo "Full metrics:"
  echo "$METRICS" | jq '.'
  exit 1
fi









