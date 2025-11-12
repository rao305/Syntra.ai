# Release Checklist v0.1-phase1

## Pre-Release ✅

- [x] All Phase-1 features implemented
- [x] All tests passing (with mock provider)
- [x] Documentation complete
- [x] Feature flags locked
- [x] CI guardrail configured

## Release Tag ✅

- [x] Tag created: `v0.1-phase1`
- [x] Release notes: `RELEASE_NOTES_v0.1-phase1.md`
- [x] Version info: `VERSION.md`

## Feature Flags (Locked) ✅

```bash
COALESCE_ENABLED=1          # Request coalescing
STREAM_FANOUT_ENABLED=1     # Streaming fan-out
```

**Location**: 
- `.github/workflows/ttft-check.yml` (CI)
- Environment variables for runtime

## CI Guardrail ✅

- [x] `.github/workflows/ttft-check.yml` uses mock provider
- [x] `TTFT_PROVIDER=mock` set in CI
- [x] `TTFT_MODEL=faststream-ttft` set in CI
- [x] Deterministic results (< 300ms)

## Post-Release

- [ ] Push tag to remote: `git push origin v0.1-phase1`
- [ ] Create GitHub release (optional)
- [ ] Notify team
- [ ] Update production deployment

## Verification

```bash
# Verify tag
git tag -l "v0.1-phase1"
git show v0.1-phase1

# Verify CI config
grep -A 5 "TTFT_PROVIDER" .github/workflows/ttft-check.yml

# Verify flags
grep "COALESCE_ENABLED\|STREAM_FANOUT_ENABLED" .github/workflows/ttft-check.yml
```

---

**Status**: ✅ **READY TO PUSH**


