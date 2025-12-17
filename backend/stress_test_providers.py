#!/usr/bin/env python3
"""Stress test all AI providers and check rate limits."""
import asyncio
import httpx
import time
from datetime import datetime
from typing import Dict, List, Any
import json

# Configuration
BASE_URL = "http://localhost:8000"
ORG_ID = "org_demo"
USER_ID = "c76be13c-77aa-48ae-aed2-9fceeb1c8e53"  # Valid user: demo@example.com

# Provider configurations
PROVIDERS = {
    "openai": {"model": "gpt-4o-mini", "enabled": True, "concurrency": 10},
    "gemini": {"model": "gemini-2.0-flash-exp", "enabled": True, "concurrency": 2},  # Low concurrency to respect 10/min limit
    "kimi": {"model": "moonshot-v1-8k", "enabled": True, "concurrency": 3},  # Max 3 concurrent
    "perplexity": {"model": "sonar", "enabled": True, "concurrency": 5},
    "openrouter": {"model": "anthropic/claude-3.5-sonnet", "enabled": False},  # Disabled per user request
}

# Test parameters
CONCURRENT_REQUESTS = 10  # Default number of concurrent requests per provider
TOTAL_REQUESTS_PER_PROVIDER = 10  # Reduced from 20 to respect rate limits
REQUEST_DELAY = 3.0  # Increased delay between batches (seconds) to respect rate limits


class ProviderTestResult:
    """Results for a single provider test."""

    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limited = 0
        self.out_of_quota = 0
        self.auth_errors = 0
        self.other_errors = 0
        self.latencies: List[float] = []
        self.error_messages: List[str] = []
        self.start_time = None
        self.end_time = None

    def add_success(self, latency: float):
        """Record a successful request."""
        self.successful_requests += 1
        self.latencies.append(latency)

    def add_failure(self, status_code: int, error_msg: str):
        """Record a failed request."""
        self.failed_requests += 1

        if status_code == 429:
            self.rate_limited += 1
        elif status_code == 402 or "quota" in error_msg.lower() or "insufficient" in error_msg.lower():
            self.out_of_quota += 1
        elif status_code == 401 or status_code == 403:
            self.auth_errors += 1
        else:
            self.other_errors += 1

        self.error_messages.append(f"[{status_code}] {error_msg}")

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0

        return {
            "provider": self.provider,
            "model": self.model,
            "total_requests": self.total_requests,
            "successful": self.successful_requests,
            "failed": self.failed_requests,
            "success_rate": f"{(self.successful_requests / self.total_requests * 100):.1f}%" if self.total_requests > 0 else "0%",
            "rate_limited": self.rate_limited,
            "out_of_quota": self.out_of_quota,
            "auth_errors": self.auth_errors,
            "other_errors": self.other_errors,
            "avg_latency_ms": sum(self.latencies) / len(self.latencies) if self.latencies else 0,
            "min_latency_ms": min(self.latencies) if self.latencies else 0,
            "max_latency_ms": max(self.latencies) if self.latencies else 0,
            "duration_seconds": duration,
            "requests_per_second": self.total_requests / duration if duration > 0 else 0,
            "sample_errors": self.error_messages[:5]  # Show first 5 errors
        }


async def test_provider_single_request(
    client: httpx.AsyncClient,
    provider: str,
    model: str,
    result: ProviderTestResult
) -> None:
    """Make a single test request to a provider."""
    result.total_requests += 1

    start_time = time.time()

    try:
        # Create a test thread first
        thread_response = await client.post(
            f"{BASE_URL}/api/threads/",
            headers={
                "x-org-id": ORG_ID,
                "Content-Type": "application/json"
            },
            json={
                "user_id": USER_ID,
                "title": f"Stress test {provider} {datetime.now().isoformat()}"
            },
            timeout=30.0
        )

        if thread_response.status_code != 200:
            result.add_failure(thread_response.status_code, "Failed to create thread")
            return

        thread_id = thread_response.json()["thread_id"]

        # Send a message
        message_response = await client.post(
            f"{BASE_URL}/api/threads/{thread_id}/messages",
            headers={
                "x-org-id": ORG_ID,
                "Content-Type": "application/json"
            },
            json={
                "user_id": USER_ID,
                "content": "Say 'OK' if you can hear me.",
                "provider": provider,
                "model": model,
                "reason": "stress_test"
            },
            timeout=30.0
        )

        latency = (time.time() - start_time) * 1000  # Convert to ms

        if message_response.status_code == 200:
            result.add_success(latency)
        else:
            error_data = message_response.text
            try:
                error_json = message_response.json()
                error_msg = error_json.get("detail", error_data)
            except:
                error_msg = error_data

            result.add_failure(message_response.status_code, str(error_msg))

    except httpx.TimeoutException:
        result.add_failure(408, "Request timeout")
    except Exception as e:
        result.add_failure(500, str(e))


async def stress_test_provider(provider: str, model: str, num_requests: int, concurrency: int) -> ProviderTestResult:
    """Stress test a single provider."""
    result = ProviderTestResult(provider, model)
    result.start_time = time.time()

    async with httpx.AsyncClient() as client:
        # Run requests in batches
        for batch_start in range(0, num_requests, concurrency):
            batch_size = min(concurrency, num_requests - batch_start)

            # Create concurrent tasks
            tasks = [
                test_provider_single_request(client, provider, model, result)
                for _ in range(batch_size)
            ]

            # Wait for batch to complete
            await asyncio.gather(*tasks)

            # Small delay between batches
            if batch_start + batch_size < num_requests:
                await asyncio.sleep(REQUEST_DELAY)

    result.end_time = time.time()
    return result


async def get_provider_status() -> Dict[str, Any]:
    """Get current provider status from API."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/api/orgs/{ORG_ID}/providers/status",
                headers={"x-org-id": ORG_ID},
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Status code: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}


async def main():
    """Run stress tests on all providers."""
    print("=" * 80)
    print("AI PROVIDER STRESS TEST")
    print("=" * 80)
    print(f"Configuration:")
    print(f"  - Concurrent requests: {CONCURRENT_REQUESTS}")
    print(f"  - Total requests per provider: {TOTAL_REQUESTS_PER_PROVIDER}")
    print(f"  - Request delay: {REQUEST_DELAY}s")
    print(f"  - Organization: {ORG_ID}")
    print("=" * 80)
    print()

    # Get initial provider status
    print("Fetching provider status...")
    status = await get_provider_status()

    if "providers" in status:
        print("\nProvider Status BEFORE Testing:")
        print("-" * 80)
        for provider in status["providers"]:
            configured = "✓ Configured" if provider["configured"] else "✗ Not Configured"
            usage = provider.get("usage", {})
            print(f"{provider['provider']:15} {configured:20} "
                  f"Requests: {usage.get('requests_today', 0)}/{usage.get('request_limit', 0)} "
                  f"Tokens: {usage.get('tokens_today', 0)}/{usage.get('token_limit', 0)}")
        print("-" * 80)
        print()

    # Run stress tests
    print("Starting stress tests...")
    print()

    results = []

    for provider, config in PROVIDERS.items():
        if not config["enabled"]:
            print(f"⊘ Skipping {provider} (disabled in configuration)")
            continue

        # Use provider-specific concurrency if available, otherwise use default
        concurrency = config.get("concurrency", CONCURRENT_REQUESTS)

        print(f"Testing {provider} ({config['model']}) [concurrency: {concurrency}]...")
        result = await stress_test_provider(
            provider,
            config["model"],
            TOTAL_REQUESTS_PER_PROVIDER,
            concurrency
        )
        results.append(result)
        print(f"  ✓ Completed: {result.successful_requests}/{result.total_requests} successful")
        print()

    # Get final provider status
    print("\nFetching final provider status...")
    final_status = await get_provider_status()

    # Print results
    print("\n" + "=" * 80)
    print("STRESS TEST RESULTS")
    print("=" * 80)
    print()

    providers_with_issues = []

    for result in results:
        stats = result.get_stats()

        print(f"Provider: {stats['provider'].upper()}")
        print(f"  Model: {stats['model']}")
        print(f"  Total Requests: {stats['total_requests']}")
        print(f"  Successful: {stats['successful']} ({stats['success_rate']})")
        print(f"  Failed: {stats['failed']}")

        if stats['rate_limited'] > 0:
            print(f"  ⚠️  Rate Limited: {stats['rate_limited']} requests")
            providers_with_issues.append((stats['provider'], 'RATE_LIMITED'))

        if stats['out_of_quota'] > 0:
            print(f"  ❌ Out of Quota: {stats['out_of_quota']} requests")
            providers_with_issues.append((stats['provider'], 'OUT_OF_QUOTA'))

        if stats['auth_errors'] > 0:
            print(f"  🔒 Auth Errors: {stats['auth_errors']} requests")
            providers_with_issues.append((stats['provider'], 'AUTH_ERROR'))

        if stats['other_errors'] > 0:
            print(f"  ⚠️  Other Errors: {stats['other_errors']} requests")

        if stats['successful'] > 0:
            print(f"  Avg Latency: {stats['avg_latency_ms']:.0f}ms")
            print(f"  Min/Max Latency: {stats['min_latency_ms']:.0f}ms / {stats['max_latency_ms']:.0f}ms")

        print(f"  Duration: {stats['duration_seconds']:.2f}s")
        print(f"  Requests/sec: {stats['requests_per_second']:.2f}")

        if stats['sample_errors']:
            print(f"  Sample Errors:")
            for error in stats['sample_errors'][:3]:
                print(f"    - {error}")

        print()

    # Print final status
    if "providers" in final_status:
        print("\nProvider Status AFTER Testing:")
        print("-" * 80)
        for provider in final_status["providers"]:
            configured = "✓" if provider["configured"] else "✗"
            usage = provider.get("usage", {})
            req_usage = usage.get('requests_today', 0)
            req_limit = usage.get('request_limit', 0)
            tok_usage = usage.get('tokens_today', 0)
            tok_limit = usage.get('token_limit', 0)

            req_pct = (req_usage / req_limit * 100) if req_limit > 0 else 0
            tok_pct = (tok_usage / tok_limit * 100) if tok_limit > 0 else 0

            status_icon = "✓"
            if req_pct > 90 or tok_pct > 90:
                status_icon = "⚠️"
            if req_usage >= req_limit or tok_usage >= tok_limit:
                status_icon = "❌"

            print(f"{status_icon} {provider['provider']:15} {configured} "
                  f"Requests: {req_usage}/{req_limit} ({req_pct:.0f}%) "
                  f"Tokens: {tok_usage}/{tok_limit} ({tok_pct:.0f}%)")
        print("-" * 80)
        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if providers_with_issues:
        print("\n⚠️  PROVIDERS WITH ISSUES:")
        issue_types = {}
        for provider, issue_type in providers_with_issues:
            if issue_type not in issue_types:
                issue_types[issue_type] = []
            if provider not in issue_types[issue_type]:
                issue_types[issue_type].append(provider)

        for issue_type, providers in issue_types.items():
            print(f"  {issue_type}: {', '.join(providers)}")
    else:
        print("\n✓ All providers working normally!")

    # Check for providers at risk
    if "providers" in final_status:
        at_risk = []
        for provider in final_status["providers"]:
            if provider["configured"]:
                usage = provider.get("usage", {})
                req_pct = (usage.get('requests_today', 0) / usage.get('request_limit', 1)) * 100
                tok_pct = (usage.get('tokens_today', 0) / usage.get('token_limit', 1)) * 100

                if req_pct > 80 or tok_pct > 80:
                    at_risk.append({
                        "provider": provider['provider'],
                        "req_pct": req_pct,
                        "tok_pct": tok_pct
                    })

        if at_risk:
            print("\n⚠️  PROVIDERS NEAR LIMIT (>80%):")
            for p in at_risk:
                print(f"  {p['provider']}: Requests {p['req_pct']:.0f}%, Tokens {p['tok_pct']:.0f}%")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
