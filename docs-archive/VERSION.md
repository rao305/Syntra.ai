# Version Information

## Current Release

**Version**: v0.1-phase1  
**Date**: 2025-01-11  
**Status**: Phase-1 Complete

## Feature Flags (Locked)

```bash
COALESCE_ENABLED=1          # Request coalescing (enabled)
STREAM_FANOUT_ENABLED=1     # Streaming fan-out (enabled)
```

These flags are locked in v0.1-phase1. To disable for debugging, modify environment variables.

## CI Configuration

- TTFT checks use mock provider (`TTFT_PROVIDER=mock`)
- Deterministic results (always < 300ms)
- Prevents flaky CI due to provider latency

## Release Notes

See `RELEASE_NOTES_v0.1-phase1.md` for complete details.

## Git Tag

```bash
git tag -l "v0.1-phase1"
git show v0.1-phase1
```

## Next Release

Phase-2 features (TBD)


