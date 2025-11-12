# Production Cutover Checklist

**Date**: ___________  
**Owner**: ___________  

## Pre-Cutover

- [ ] `restore_prod_settings.sh` applied; backend restarted
- [ ] `COALESCE_ENABLED=1` left enabled
- [ ] `STREAM_FANOUT_ENABLED=1` left enabled
- [ ] CI guardrail `.github/workflows/ttft-check.yml` merged
- [ ] All test scripts verified and committed

## Monitoring & Alerts

- [ ] Alerts wired (`check_alerts.sh` or monitoring system)
- [ ] Alert thresholds configured:
  - [ ] `ttft_ms.p95 > 1500` (5 min window)
  - [ ] `error_rate > 1%` (last 100 requests)
  - [ ] `queue_wait_ms.p95 > 1000` (5 min window)
  - [ ] `coalesce.followers/leaders < 10` under burst
- [ ] Dashboard shows:
  - [ ] TTFT p95
  - [ ] Latency p95
  - [ ] Queue wait p95
  - [ ] Coalesce leaders/followers
  - [ ] Error rate

## Rollback Plan

- [ ] Rollback notes documented (flags + pacer knobs)
- [ ] Team trained on rollback procedure:
  1. Set `STREAM_FANOUT_ENABLED=0` (keeps streaming per-client)
  2. Set `COALESCE_ENABLED=0` (disables coalescer)
  3. Tighten pacer if provider 429s occur
  4. Route to non-stream endpoint if needed

## Production Settings

Verify these are set:
```bash
PERPLEXITY_RPS=1
PERPLEXITY_CONCURRENCY=3
PERPLEXITY_BURST=2
COALESCE_ENABLED=1
STREAM_FANOUT_ENABLED=1
```

## Post-Cutover Verification

- [ ] Metrics endpoint accessible: `/api/metrics/performance?last_n=100`
- [ ] Alert check script works: `./check_alerts.sh`
- [ ] Burst test passes (50 concurrent, single thread)
- [ ] Streaming works (TTFT < 1.5s)
- [ ] Cancel works (< 300ms)

## Sign-Off

- [ ] All items checked
- [ ] Team notified
- [ ] Monitoring active
- [ ] Rollback plan ready

**Cutover Date**: ___________  
**Cutover By**: ___________  
**Status**: ⏳ PENDING / ✅ COMPLETE


