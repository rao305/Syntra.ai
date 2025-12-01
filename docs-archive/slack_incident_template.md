# Slack Incident Template

## Quick Copy-Paste Template

```
🚨 DAC Phase 4 Incident

**Status**: Investigating
**Severity**: P0/P1/P2
**Component**: API/Router/Cache/Provider
**Started**: [timestamp]

**Symptoms**:
- [Brief description]

**Impact**:
- [User impact]
- [Traffic affected]

**Actions Taken**:
- [ ] Feature flag rollback (DAC_SSE_V2=0)
- [ ] Provider ladder adjusted
- [ ] Cache TTL increased
- [ ] On-call notified

**Next Steps**:
- [ ] [Action item]
- [ ] [Action item]

**Runbook**: https://github.com/your-org/dac/blob/main/PHASE4_INCIDENT_RUNBOOK.md
**Dashboard**: [Link to Grafana/Prometheus]
```

## Usage

1. Copy template to Slack #dac-incidents channel
2. Fill in details
3. Update status as incident progresses
4. Post resolution summary when resolved

## Status Updates

**Investigating** → **Mitigating** → **Resolved**

Update every 15-30 minutes during active incident.

