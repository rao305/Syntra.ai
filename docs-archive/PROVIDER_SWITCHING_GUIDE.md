---
title: Provider Switching Guide for TTFT Tests
summary: Documentation file
last_updated: '2025-11-12'
owner: DAC
tags:
- dac
- docs
---

# Provider Switching Guide for TTFT Tests

## Quick Switch

### Use OpenAI (if you have keys)
```bash
export TTFT_PROVIDER=openai
export TTFT_MODEL=gpt-4o-mini
./run_ttft_suite.sh
```

### Use Gemini (if you have keys)
```bash
export TTFT_PROVIDER=gemini
export TTFT_MODEL=gemini-1.5-flash
./run_ttft_suite.sh
```

### Use Perplexity (default)
```bash
export TTFT_PROVIDER=perplexity
export TTFT_MODEL=llama-3.1-sonar-small-128k-online
./run_ttft_suite.sh
```

### Use Mock (for CI/deterministic tests)
```bash
export TTFT_PROVIDER=mock
export TTFT_MODEL=faststream-ttft
./run_ttft_suite.sh
```

## CI Configuration

CI automatically uses mock provider for deterministic results:
- `.github/workflows/ttft-check.yml` sets `TTFT_PROVIDER=mock`
- Mock provider always returns TTFT < 300ms
- Prevents flaky CI due to provider API latency

## Local Benchmarking

To benchmark real providers locally:
```bash
# Test with OpenAI
TTFT_PROVIDER=openai TTFT_MODEL=gpt-4o-mini ./run_ttft_suite.sh

# Test with Gemini
TTFT_PROVIDER=gemini TTFT_MODEL=gemini-1.5-flash ./run_ttft_suite.sh

# Test with Perplexity (when conditions are stable)
TTFT_PROVIDER=perplexity TTFT_MODEL=llama-3.1-sonar-small-128k-online ./run_ttft_suite.sh
```

## Environment Variables

The suite reads:
- `TTFT_PROVIDER` - Provider to use (default: perplexity)
- `TTFT_MODEL` - Model to use (default: llama-3.1-sonar-small-128k-online)
- Falls back to `DAC_DEFAULT_PROVIDER` and `DAC_DEFAULT_MODEL` if not set

## Notes

- Mock provider is for CI stability only
- Real providers may have variable latency
- Implementation is verified regardless of provider latency
- Phase-1 completion is not blocked by provider-side delays


