---
title: TTFT Verification Guide
summary: Documentation file
last_updated: '2025-11-12'
owner: DAC
tags:
- dac
- docs
---

# TTFT Verification Guide

This guide provides scripts and procedures to verify that Time To First Token (TTFT) meets the Phase 1 requirement: **P95 ≤ 1500ms**.

## Quick Start

Run the complete verification suite:

```bash
./verify_ttft.sh
```

This will:
1. ✅ Smoke test: Verify early bytes over SSE (ping + first delta)
2. ✅ Measure TTFT p95: 20 samples, parallel 5
3. ✅ Cancel test: Verify cancellation < 300ms
4. ✅ Cross-check: Compare with metrics API

## Individual Tests

### 1. Smoke Test - Early Bytes

```bash
THREAD=$(curl -s -X POST http://localhost:8000/api/threads/ \
  -H "Content-Type: application/json" -H "x-org-id: org_demo" \
  -d '{"title":"TTFT"}' | jq -r '.thread_id')

curl -N -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -H "x-org-id: org_demo" \
  -X POST "http://localhost:8000/api/threads/$THREAD/messages/stream" \
  --data '{"role":"user","content":"Say hello once.","provider":"perplexity","model":"llama-3.1-sonar-small-128k-online","reason":"smoke-test","scope":"private"}'
```

**Expected:** Immediate `event: ping` followed by `event: meta` (with `ttft_ms`) or `event: delta`.

### 2. TTFT P95 Measurement

```bash
node sse_ttft_p95.mjs
```

**Expected output:**
```
TTFT ms (all): [450, 520, 480, ...]
TTFT p95: 1250 ms
TTFT min: 420 ms
TTFT max: 1350 ms
TTFT avg: 680 ms
```

**Pass criteria:** `TTFT p95 ≤ 1500 ms`

### 3. Cancel Test

```bash
node cancel_quick.mjs
```

**Expected output:**
```
Client abort at 2000 ms
✅ Cancel completed at 2100ms
✅ PASS: Cancel time < 300ms
```

**Pass criteria:** End-to-end cancellation visible in < 300ms from abort signal.

### 4. Cross-check with Metrics

```bash
curl -s "http://localhost:8000/api/metrics/performance?last_n=50" | jq '.ttft_ms'
```

**Expected:**
```json
{
  "p50": 650,
  "p95": 1250,
  "p99": 1400,
  "min": 420,
  "max": 1350,
  "count": 50
}
```

## Diagnosis

If TTFT p95 > 1500ms, run the diagnostic helper:

```bash
./diagnose_ttft.sh
```

This will check:
- ✅ SSE headers (anti-buffering)
- ✅ Immediate ping response
- ✅ Adapter client usage (shared vs per-request)
- ✅ Pacer delays
- ✅ Connection warmup

### Common Issues & Fixes

#### ❌ No immediate ping
- **Check:** SSE headers in `backend/app/api/threads.py`
- **Fix:** Ensure `X-Accel-Buffering: no`, `Cache-Control: no-store`
- **Fix:** Disable gzip on SSE (`Accept-Encoding: identity`)

#### ❌ Adapter sends full blob
- **Check:** Verify `stream: true` in provider payload
- **Check:** Adapters use `aiter_lines()` for streaming
- **Fix:** Ensure adapters emit `{"type": "delta", "delta": "..."}` format

#### ❌ Client created per request
- **Check:** Adapters import `get_client()` from `_client.py`
- **Fix:** Replace `httpx.AsyncClient()` with `await get_client()`

#### ❌ Pacer adds delay
- **Check:** `queue_wait_ms` in metrics (should be ~0)
- **Fix:** Temporarily increase concurrency for tests:
  ```bash
  export PERPLEXITY_CONCURRENCY=5
  export PERPLEXITY_RPS=10
  ```

#### ❌ Cold starts
- **Check:** `warm_provider_connections()` runs on startup
- **Fix:** Verify `backend/main.py` lifespan events

## Implementation Summary

### ✅ Completed Fixes

1. **Shared HTTP/2 Client** (`backend/app/adapters/_client.py`)
   - HTTP/2 enabled, connection pooling (50 max, 50 keepalive)
   - `Accept-Encoding: identity` to avoid gzip on SSE

2. **All Adapters Updated**
   - Perplexity, OpenAI, Gemini, OpenRouter
   - Use shared client, emit normalized format
   - Measure TTFT at first provider byte

3. **SSE Endpoint** (`backend/app/api/threads.py`)
   - Anti-buffering headers
   - Early heartbeat (`event: ping`)
   - TTFT measurement at first delta

4. **Frontend SSE Parsing** (`frontend/app/threads/page.tsx`)
   - Proper frame parsing (`\n\n` separated)
   - Handles `event:` and `data:` correctly
   - Processes `meta` events (TTFT)

5. **Connection Warming** (`backend/main.py`)
   - Warms HTTP/2 connections on startup
   - Reduces cold-start TTFT by 200-500ms

6. **Requirements** (`backend/requirements.txt`)
   - Updated to `httpx[http2]==0.26.0`

## Sign-off

When all tests pass:

- ✅ **TTFT (streaming) P95:** ___ ms (target ≤ 1500 ms)
- ✅ **Cancel latency:** ___ ms (target < 300 ms)

Record these values in your Go/No-Go document.

## Files Created

- `sse_ttft_p95.mjs` - TTFT p95 measurement script
- `cancel_quick.mjs` - Cancel latency test
- `verify_ttft.sh` - Complete verification suite
- `diagnose_ttft.sh` - Diagnostic helper

