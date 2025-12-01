---
title: Alerting & Monitoring Guide
summary: Documentation file
last_updated: '2025-11-12'
owner: DAC
tags:
- dac
- docs
---

# Alerting & Monitoring Guide

## Metrics Endpoint

All metrics available at:
```
GET /api/metrics/performance?last_n=<count>
```

## Critical Alerts

### 1. TTFT Regression
**Threshold**: `ttft_ms.p95 > 1500` for 5 minutes

**Query**:
```bash
curl -s "http://localhost:8000/api/metrics/performance?last_n=100" | \
  jq '.ttft_ms.p95'
```

**Action**: 
- Check SSE headers (anti-buffering)
- Verify shared HTTP/2 client usage
- Check for proxy buffering
- Verify connection warming ran

### 2. Error Rate Spike
**Threshold**: `error_rate > 1%` over last 100 requests

**Query**:
```bash
curl -s "http://localhost:8000/api/metrics/performance?last_n=100" | \
  jq '.error_rate'
```

**Action**:
- Check provider API status
- Review error logs
- Verify rate limits
- Check pacer configuration

### 3. Queue Saturation
**Threshold**: `queue_wait_ms.p95 > 1000` for 5 minutes

**Query**:
```bash
curl -s "http://localhost:8000/api/metrics/performance?last_n=100" | \
  jq '.queue_wait_ms.p95'
```

**Action**:
- Increase pacer concurrency (if within limits)
- Check provider rate limits
- Verify pacer configuration
- Consider scaling

### 4. Coalescing Efficiency Drop
**Threshold**: `coalesce.followers/coalesce.leaders < 10` under burst

**Query**:
```bash
curl -s "http://localhost:8000/api/metrics/performance?last_n=100" | \
  jq '{leaders: .coalesce.leaders, followers: .coalesce.followers, ratio: (.coalesce.followers / .coalesce.leaders)}'
```

**Action**:
- Check coalesce key generation (should be stable)
- Verify stream hub subscription logic
- Check for non-idempotent operations bypassing coalescing
- Review feature flag: `COALESCE_ENABLED=1`

## Monitoring Script

Save as `check_alerts.sh`:

```bash
#!/bin/bash
# Quick alert check

METRICS=$(curl -s "http://localhost:8000/api/metrics/performance?last_n=100")

TTFT_P95=$(echo "$METRICS" | jq -r '.ttft_ms.p95 // "N/A"')
ERROR_RATE=$(echo "$METRICS" | jq -r '.error_rate // "N/A"')
QUEUE_WAIT_P95=$(echo "$METRICS" | jq -r '.queue_wait_ms.p95 // "N/A"')
LEADERS=$(echo "$METRICS" | jq -r '.coalesce.leaders // 0')
FOLLOWERS=$(echo "$METRICS" | jq -r '.coalesce.followers // 0')

echo "=== Alert Check ==="
echo ""

# TTFT check
if [ "$TTFT_P95" != "N/A" ] && awk "BEGIN {exit !($TTFT_P95 > 1500)}" 2>/dev/null; then
  echo "⚠️  TTFT regression: p95=${TTFT_P95}ms > 1500ms"
else
  echo "✅ TTFT p95: ${TTFT_P95}ms"
fi

# Error rate check
if [ "$ERROR_RATE" != "N/A" ] && awk "BEGIN {exit !($ERROR_RATE > 0.01)}" 2>/dev/null; then
  echo "⚠️  Error rate high: ${ERROR_RATE} > 1%"
else
  echo "✅ Error rate: ${ERROR_RATE}"
fi

# Queue wait check
if [ "$QUEUE_WAIT_P95" != "N/A" ] && awk "BEGIN {exit !($QUEUE_WAIT_P95 > 1000)}" 2>/dev/null; then
  echo "⚠️  Queue saturation: p95=${QUEUE_WAIT_P95}ms > 1000ms"
else
  echo "✅ Queue wait p95: ${QUEUE_WAIT_P95}ms"
fi

# Coalescing check
if [ "$LEADERS" -gt 0 ]; then
  RATIO=$(awk "BEGIN {printf \"%.1f\", $FOLLOWERS/$LEADERS}")
  if awk "BEGIN {exit !($RATIO < 10)}" 2>/dev/null; then
    echo "⚠️  Coalescing efficiency low: ratio=${RATIO} (followers/leaders)"
  else
    echo "✅ Coalescing ratio: ${RATIO} (followers/leaders)"
  fi
else
  echo "ℹ️  No coalescing data yet"
fi

echo ""
echo "Full metrics:"
echo "$METRICS" | jq '.'
```

## Integration Examples

### Prometheus (if using)
```yaml
# Example alert rules
groups:
  - name: dac_alerts
    rules:
      - alert: TTFTRegression
        expr: dac_ttft_p95 > 1500
        for: 5m
        annotations:
          summary: "TTFT p95 exceeded 1500ms"
      
      - alert: HighErrorRate
        expr: dac_error_rate > 0.01
        for: 1m
        annotations:
          summary: "Error rate exceeded 1%"
      
      - alert: QueueSaturation
        expr: dac_queue_wait_p95 > 1000
        for: 5m
        annotations:
          summary: "Queue wait p95 exceeded 1000ms"
```

### Simple Cron Check
```bash
# Add to crontab: */5 * * * * /path/to/check_alerts.sh
# Runs every 5 minutes
```

## Feature Flags to Keep Enabled

```bash
COALESCE_ENABLED=1          # Request coalescing (critical for efficiency)
STREAM_FANOUT_ENABLED=1     # Streaming fan-out (reduces provider calls)
```

## Error TTL Configuration

Keep error TTL at ~2s to prevent shared-failure pinning:
- Short enough to recover quickly
- Long enough to prevent thundering herd
- Prevents all coalesced requests from failing together

## Production Settings

After testing, restore:
```bash
source restore_prod_settings.sh
```

This sets:
- `PERPLEXITY_RPS=1`
- `PERPLEXITY_CONCURRENCY=3`
- `PERPLEXITY_BURST=2`

Safe for free tier usage.


