# Quick Sign-Off Guide

## One-Command Sign-Off

```bash
./final_sign_off.sh
```

This will:
1. ✅ Prep test environment
2. ✅ Run full TTFT suite
3. ✅ Auto-append results to `PHASE1_GO_NO_GO.md`
4. ✅ Restore production settings

**Note**: You'll need to restart the backend twice (after prep and after restore).

## Manual Sign-Off (if needed)

```bash
# 1) Prep
source prep_ttft_test.sh
# restart backend

# 2) Run suite
./run_ttft_suite.sh | tee /tmp/ttft_results.txt

# 3) Append results
awk '/^• TTFT|^• Cancel latency|^• Queue wait/ {print}' /tmp/ttft_results.txt >> PHASE1_GO_NO_GO.md

# 4) Restore production
source restore_prod_settings.sh
# restart backend
```

## PASS Stamp Template

If your suite prints green, paste this into `PHASE1_GO_NO_GO.md`:

```
## Phase-1 Final Verification — PASS

• TTFT (streaming) p95: ____ ms (target ≤ 1,500 ms) — PASS
• Cancel latency: ____ ms (target < 300 ms) — PASS
• Queue wait p95 (TTFT run): ____ ms (≈0) — OK

**Decision**: ✅ Proceed to Phase-2
```

## 90-Second Triage (if red)

1. **No early ping** → Check SSE headers (`text/event-stream`, `no-store`, `X-Accel-Buffering: no`) and disable gzip/buffering
2. **TTFT > 1.5s but queue_wait_ms > 0** → Re-source `prep_ttft_test.sh` (RPS/CONC=5), rerun
3. **Single big delta** → Ensure adapters send `stream:true` and iterate `aiter_lines()`; confirm normalized delta frames
4. **Cold spikes** → Confirm warmup ran on startup

## Production Cutover

After sign-off, complete `PRODUCTION_CUTOVER_CHECKLIST.md`:
- [ ] Production settings applied
- [ ] Alerts wired
- [ ] Dashboard configured
- [ ] Rollback plan documented


