# Phase 1 - Ready for Final Sign-Off

## Status: ✅ **ONE RUN AWAY**

All implementation complete. All tests ready. One verification run needed.

## Final Run Order

```bash
# 1. Prep (one-time)
source prep_ttft_test.sh
# Restart backend

# 2. Run suite
./run_ttft_suite.sh

# 3. Copy results to PHASE1_GO_NO_GO.md
# (Three lines printed at end)

# 4. Restore production
source restore_prod_settings.sh
# Restart backend
```

## Pass Criteria

✅ **TTFT (streaming) p95**: ≤ 1,500 ms  
✅ **Cancel latency**: < 300 ms  
✅ **Queue wait p95 (TTFT run)**: ≈ 0 ms

## What's Already Locked In ✅

### Core Performance
- **Burst**: 50/50 success → 2 messages, 1 upstream call
- **Error rate**: 0% under load
- **Latency P95**: ~6.8s (within target)
- **Queue wait P95**: 0ms

### Streaming Infrastructure
- Pooled HTTP/2 client
- Early ping on SSE
- Normalized deltas
- TTFT meta at first byte
- Frontend SSE parsing

### Operational
- CI guardrail (`.github/workflows/ttft-check.yml`)
- Restore script (`restore_prod_settings.sh`)
- Feature flags enabled
- Error TTL configured

## Hardening Knobs (Keep Enabled)

```bash
COALESCE_ENABLED=1          # Request coalescing
STREAM_FANOUT_ENABLED=1     # Streaming fan-out
```

**Error TTL**: ~2s (prevents shared-failure pinning)

## Alerting

See `ALERTING_GUIDE.md` for complete monitoring setup.

**Quick check**: `./check_alerts.sh`

**Thresholds**:
- TTFT regression: `ttft_ms.p95 > 1500` for 5 min
- Error rate: `error_rate > 1%` over last 100
- Queue saturation: `queue_wait_ms.p95 > 1000`
- Coalescing: `coalesce.followers/leaders < 10` under burst

## Files Ready

### Test Scripts
- ✅ `prep_ttft_test.sh` - Test environment
- ✅ `run_ttft_suite.sh` - Complete suite
- ✅ `smoke_ttft.sh` - Early bytes check
- ✅ `sse_ttft_p95.mjs` - TTFT measurement
- ✅ `cancel_quick.mjs` - Cancel test
- ✅ `restore_prod_settings.sh` - Production restore

### Monitoring
- ✅ `check_alerts.sh` - Quick alert check
- ✅ `ALERTING_GUIDE.md` - Complete guide

### Documentation
- ✅ `FINAL_SIGN_OFF.md` - Sign-off checklist
- ✅ `PHASE1_GO_NO_GO.md` - Updated with pass criteria
- ✅ `PHASE1_CLOSURE_SUMMARY.md` - Complete summary

## Next Step

**Run `./run_ttft_suite.sh` and paste results → Phase 1 closed**


