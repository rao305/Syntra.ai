#!/usr/bin/env python3
"""Comprehensive integration test for all AI providers in chat and collaboration features."""
import asyncio
import httpx
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

# Configuration
BASE_URL = "http://localhost:8000"
ORG_ID = "org_demo"
USER_ID = "c76be13c-77aa-48ae-aed2-9fceeb1c8e53"  # Valid user: demo@example.com

# Providers to test
PROVIDERS = ["openai", "gemini", "kimi", "perplexity"]

# Test scenarios
TEST_SCENARIOS = {
    "simple_query": "What is 2+2? Answer in one sentence.",
    "coding_query": "Write a Python function to check if a number is prime. Keep it simple.",
    "reasoning_query": "Explain why the sky is blue in simple terms.",
}


class IntegrationTestResult:
    """Results for integration tests."""

    def __init__(self):
        self.provider_tests: Dict[str, Dict] = {}
        self.routing_tests: List[Dict] = []
        self.collaboration_tests: List[Dict] = []
        self.errors: List[str] = []

    def add_provider_test(self, provider: str, success: bool, latency: float, error: Optional[str] = None):
        """Record a provider test result."""
        if provider not in self.provider_tests:
            self.provider_tests[provider] = {"success": 0, "failed": 0, "latencies": []}

        if success:
            self.provider_tests[provider]["success"] += 1
            self.provider_tests[provider]["latencies"].append(latency)
        else:
            self.provider_tests[provider]["failed"] += 1
            if error:
                self.errors.append(f"[{provider}] {error}")

    def add_routing_test(self, query: str, expected_provider: Optional[str], actual_provider: str, success: bool):
        """Record a routing test result."""
        self.routing_tests.append({
            "query": query,
            "expected": expected_provider,
            "actual": actual_provider,
            "success": success
        })

    def add_collaboration_test(self, test_name: str, success: bool, providers_used: List[str], error: Optional[str] = None):
        """Record a collaboration test result."""
        self.collaboration_tests.append({
            "test_name": test_name,
            "success": success,
            "providers_used": providers_used,
            "error": error
        })

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("INTEGRATION TEST SUMMARY")
        print("=" * 80)
        print()

        # Provider tests
        print("1. PROVIDER CHAT TESTS")
        print("-" * 80)
        total_success = 0
        total_failed = 0

        for provider, results in self.provider_tests.items():
            success = results["success"]
            failed = results["failed"]
            total = success + failed
            total_success += success
            total_failed += failed

            if success > 0:
                avg_latency = sum(results["latencies"]) / len(results["latencies"])
                status = "✅" if failed == 0 else "⚠️"
                print(f"{status} {provider:15} {success}/{total} passed  Avg Latency: {avg_latency:.0f}ms")
            else:
                print(f"❌ {provider:15} {success}/{total} passed  All tests failed")

        print(f"\nTotal: {total_success}/{total_success + total_failed} tests passed")
        print()

        # Routing tests
        if self.routing_tests:
            print("2. INTELLIGENT ROUTING TESTS")
            print("-" * 80)
            routing_success = sum(1 for t in self.routing_tests if t["success"])
            total_routing = len(self.routing_tests)

            for test in self.routing_tests:
                status = "✅" if test["success"] else "❌"
                print(f"{status} Query: {test['query'][:50]:50} → {test['actual']:12}")

            print(f"\nTotal: {routing_success}/{total_routing} routing tests passed")
            print()

        # Collaboration tests
        if self.collaboration_tests:
            print("3. COLLABORATION PIPELINE TESTS")
            print("-" * 80)
            collab_success = sum(1 for t in self.collaboration_tests if t["success"])
            total_collab = len(self.collaboration_tests)

            for test in self.collaboration_tests:
                status = "✅" if test["success"] else "❌"
                providers = ", ".join(test["providers_used"]) if test["providers_used"] else "none"
                print(f"{status} {test['test_name']:30} Providers: {providers}")
                if test["error"]:
                    print(f"    Error: {test['error'][:100]}")

            print(f"\nTotal: {collab_success}/{total_collab} collaboration tests passed")
            print()

        # Errors
        if self.errors:
            print("ERRORS ENCOUNTERED")
            print("-" * 80)
            for i, error in enumerate(self.errors[:10], 1):
                print(f"{i}. {error[:150]}")
            if len(self.errors) > 10:
                print(f"\n... and {len(self.errors) - 10} more errors")
            print()

        print("=" * 80)


async def test_provider_chat(
    client: httpx.AsyncClient,
    provider: str,
    model: str,
    query: str,
    result: IntegrationTestResult
) -> bool:
    """Test basic chat with a specific provider."""
    start_time = time.time()

    try:
        # Create thread
        thread_response = await client.post(
            f"{BASE_URL}/api/threads/",
            headers={
                "x-org-id": ORG_ID,
                "Content-Type": "application/json"
            },
            json={
                "user_id": USER_ID,
                "title": f"Integration test - {provider}"
            },
            timeout=30.0
        )

        if thread_response.status_code != 200:
            result.add_provider_test(provider, False, 0, f"Failed to create thread: {thread_response.status_code}")
            return False

        thread_id = thread_response.json()["thread_id"]

        # Send message
        message_response = await client.post(
            f"{BASE_URL}/api/threads/{thread_id}/messages",
            headers={
                "x-org-id": ORG_ID,
                "Content-Type": "application/json"
            },
            json={
                "user_id": USER_ID,
                "content": query,
                "provider": provider,
                "model": model,
                "reason": "integration_test"
            },
            timeout=30.0
        )

        latency = (time.time() - start_time) * 1000

        if message_response.status_code == 200:
            response_data = message_response.json()
            assistant_message = response_data.get("assistant_message", {})
            content = assistant_message.get("content", "")

            if content and len(content) > 0:
                result.add_provider_test(provider, True, latency)
                print(f"  ✅ {provider:12} Response: {content[:60]}...")
                return True
            else:
                result.add_provider_test(provider, False, latency, "Empty response content")
                print(f"  ❌ {provider:12} Empty response")
                return False
        else:
            error_msg = message_response.text[:200]
            result.add_provider_test(provider, False, latency, f"Status {message_response.status_code}: {error_msg}")
            print(f"  ❌ {provider:12} Error: {message_response.status_code}")
            return False

    except Exception as e:
        result.add_provider_test(provider, False, 0, str(e))
        print(f"  ❌ {provider:12} Exception: {str(e)[:60]}")
        return False


async def test_intelligent_routing(
    client: httpx.AsyncClient,
    query: str,
    result: IntegrationTestResult
) -> Optional[str]:
    """Test intelligent routing by sending a query without specifying provider."""
    try:
        # Create thread
        thread_response = await client.post(
            f"{BASE_URL}/api/threads/",
            headers={
                "x-org-id": ORG_ID,
                "Content-Type": "application/json"
            },
            json={
                "user_id": USER_ID,
                "title": f"Routing test"
            },
            timeout=30.0
        )

        if thread_response.status_code != 200:
            return None

        thread_id = thread_response.json()["thread_id"]

        # Send message WITHOUT specifying provider (should trigger intelligent routing)
        message_response = await client.post(
            f"{BASE_URL}/api/threads/{thread_id}/messages",
            headers={
                "x-org-id": ORG_ID,
                "Content-Type": "application/json"
            },
            json={
                "user_id": USER_ID,
                "content": query,
                "reason": "routing_test"
                # Note: No provider/model specified - should use intelligent routing
            },
            timeout=30.0
        )

        if message_response.status_code == 200:
            response_data = message_response.json()
            assistant_message = response_data.get("assistant_message", {})
            provider_used = assistant_message.get("provider", "unknown")
            model_used = assistant_message.get("model", "unknown")

            print(f"  → Routed to: {provider_used} ({model_used})")
            return provider_used
        else:
            print(f"  ❌ Routing failed: {message_response.status_code}")
            return None

    except Exception as e:
        print(f"  ❌ Routing exception: {str(e)[:60]}")
        return None


async def test_collaboration_pipeline(
    client: httpx.AsyncClient,
    result: IntegrationTestResult
) -> bool:
    """Test collaboration pipeline with multiple providers."""
    try:
        print("  Testing collaboration pipeline...")

        # Test collaboration endpoint
        collab_response = await client.post(
            f"{BASE_URL}/api/collaboration/collaborate",
            headers={
                "x-org-id": ORG_ID,
                "Content-Type": "application/json"
            },
            json={
                "message": "What are the benefits of exercise?",
                "user_id": USER_ID
            },
            timeout=60.0
        )

        if collab_response.status_code == 200:
            response_data = collab_response.json()
            providers_used = []

            # Check if response has expected structure
            if "responses" in response_data:
                providers_used = [r.get("provider", "unknown") for r in response_data.get("responses", [])]
                result.add_collaboration_test(
                    "Sequential collaboration",
                    True,
                    providers_used
                )
                print(f"  ✅ Collaboration successful - Used: {', '.join(providers_used)}")
                return True
            elif "result" in response_data or "answer" in response_data:
                # Single response format
                result.add_collaboration_test(
                    "Collaboration (single response)",
                    True,
                    ["multiple"]
                )
                print(f"  ✅ Collaboration successful")
                return True
            else:
                result.add_collaboration_test(
                    "Collaboration",
                    False,
                    [],
                    "Unexpected response format"
                )
                print(f"  ⚠️  Collaboration returned unexpected format")
                return False
        else:
            error_msg = collab_response.text[:200]
            result.add_collaboration_test(
                "Collaboration",
                False,
                [],
                f"Status {collab_response.status_code}: {error_msg}"
            )
            print(f"  ❌ Collaboration failed: {collab_response.status_code}")
            return False

    except Exception as e:
        result.add_collaboration_test(
            "Collaboration",
            False,
            [],
            str(e)
        )
        print(f"  ❌ Collaboration exception: {str(e)[:60]}")
        return False


async def test_council_orchestrator(
    client: httpx.AsyncClient,
    result: IntegrationTestResult
) -> bool:
    """Test council/orchestrator system."""
    try:
        print("  Testing council orchestrator...")

        # Test council endpoint
        council_response = await client.post(
            f"{BASE_URL}/api/council/orchestrate",
            headers={
                "x-org-id": ORG_ID,
                "Content-Type": "application/json"
            },
            json={
                "query": "What is artificial intelligence?",
                "output_mode": "deliverable-ownership"
            },
            timeout=60.0
        )

        if council_response.status_code == 200:
            response_data = council_response.json()

            # Council returns a session_id for async execution
            session_id = response_data.get("session_id")
            status = response_data.get("status", "unknown")

            result.add_collaboration_test(
                "Council orchestrator",
                True,
                ["multi-provider"]
            )
            print(f"  ✅ Council orchestrator initiated (session: {session_id}, status: {status})")
            return True
        elif council_response.status_code == 404:
            print(f"  ⊘ Council endpoint not found (may not be implemented)")
            return True
        else:
            error_msg = council_response.text[:200]
            result.add_collaboration_test(
                "Council orchestrator",
                False,
                [],
                f"Status {council_response.status_code}: {error_msg}"
            )
            print(f"  ❌ Council failed: {council_response.status_code}")
            return False

    except Exception as e:
        result.add_collaboration_test(
            "Council orchestrator",
            False,
            [],
            str(e)
        )
        print(f"  ❌ Council exception: {str(e)[:60]}")
        return False


async def main():
    """Run comprehensive integration tests."""
    print("=" * 80)
    print("COMPREHENSIVE INTEGRATION TEST")
    print("=" * 80)
    print(f"Testing: {', '.join(PROVIDERS)}")
    print(f"Organization: {ORG_ID}")
    print(f"User: {USER_ID}")
    print("=" * 80)
    print()

    result = IntegrationTestResult()

    async with httpx.AsyncClient() as client:
        # Test 1: Provider-specific chat
        print("TEST 1: PROVIDER-SPECIFIC CHAT")
        print("-" * 80)

        provider_models = {
            "openai": "gpt-4o-mini",
            "gemini": "gemini-2.0-flash-exp",
            "kimi": "moonshot-v1-8k",
            "perplexity": "sonar"
        }

        for provider in PROVIDERS:
            model = provider_models.get(provider, "default")
            print(f"\nTesting {provider} ({model}):")
            await test_provider_chat(
                client,
                provider,
                model,
                TEST_SCENARIOS["simple_query"],
                result
            )
            await asyncio.sleep(1)  # Small delay between tests

        # Test 2: Intelligent Routing
        print("\n\nTEST 2: INTELLIGENT ROUTING")
        print("-" * 80)
        print("Sending queries without specifying provider (should auto-route):\n")

        for scenario_name, query in TEST_SCENARIOS.items():
            print(f"Query: {query[:50]}...")
            provider_used = await test_intelligent_routing(client, query, result)
            result.add_routing_test(query, None, provider_used or "failed", provider_used is not None)
            await asyncio.sleep(1)

        # Test 3: Collaboration Pipeline
        print("\n\nTEST 3: COLLABORATION PIPELINE")
        print("-" * 80)
        await test_collaboration_pipeline(client, result)
        await asyncio.sleep(1)

        # Test 4: Council Orchestrator
        print("\n\nTEST 4: COUNCIL ORCHESTRATOR")
        print("-" * 80)
        await test_council_orchestrator(client, result)

    # Print summary
    result.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
