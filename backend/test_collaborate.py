"""Test script for Collaborate pipeline endpoint.

Run with: python test_collaborate.py

Prerequisites:
- FastAPI server running on localhost:8000
- Thread "test-thread-1" exists in the DB
- Org ID header: "x-org-id: org_demo"
"""
import asyncio
import json
from datetime import datetime
import httpx


BASE_URL = "http://localhost:8000"
THREAD_ID = "test-thread-1"
ORG_ID = "org_demo"


# Test prompts matrix
TEST_PROMPTS = [
    {
        "name": "Simple factual",
        "message": "Who is Andrej Karpathy and what is he known for?",
        "expected_confidence": "high",
    },
    {
        "name": "Multi-part reasoning",
        "message": "Compare Tesla's FSD approach with Waymo's, focusing on data strategy and safety.",
        "expected_confidence": "medium",
    },
    {
        "name": "Ambiguous",
        "message": "Tell me about Mercury.",
        "expected_confidence": "medium",
    },
    {
        "name": "Long instruction",
        "message": "Design a learning roadmap for someone who wants to go from zero to being able to implement basic deep learning models from scratch in 6 months.",
        "expected_confidence": "high",
    },
]


def format_json(data: dict, indent: int = 2) -> str:
    """Pretty-print JSON."""
    return json.dumps(data, indent=indent, ensure_ascii=False, default=str)


def summarize_stage(stage: dict) -> str:
    """Summarize a stage for display."""
    role = stage.get("role", "unknown")
    latency = stage.get("latency_ms", 0)
    title = stage.get("title", role)
    return f"  • {title} ({latency}ms)"


async def test_collaborate(message: str, test_name: str = "Test") -> dict | None:
    """Test a single collaborate request."""
    print(f"\n{'=' * 80}")
    print(f"TEST: {test_name}")
    print(f"{'=' * 80}")
    print(f"Message: {message[:100]}...")

    payload = {
        "message": message,
        "mode": "auto",
    }

    headers = {
        "Content-Type": "application/json",
        "x-org-id": ORG_ID,
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            print(f"\n📤 Sending POST /threads/{THREAD_ID}/collaborate...")
            response = await client.post(
                f"{BASE_URL}/threads/{THREAD_ID}/collaborate",
                json=payload,
                headers=headers,
            )

        print(f"Status: {response.status_code}")

        if response.status_code != 200:
            print(f"❌ Error: {response.text}")
            return None

        data = response.json()

        # Validate basic structure
        assert "final_answer" in data, "Missing final_answer"
        assert "internal_pipeline" in data, "Missing internal_pipeline"
        assert "external_reviews" in data, "Missing external_reviews"
        assert "meta" in data, "Missing meta"

        # Extract key metrics
        final_answer = data["final_answer"]
        pipeline = data["internal_pipeline"]
        reviews = data["external_reviews"]
        meta = data["meta"]

        print(f"\n✅ Response validated!")
        print(f"\n📊 METRICS:")
        print(f"  Run ID: {meta['run_id']}")
        print(f"  Total latency: {meta.get('total_latency_ms', 0)}ms ({meta.get('total_latency_ms', 0) / 1000:.2f}s)")
        print(f"  Confidence: {final_answer.get('explanation', {}).get('confidence_level', 'unknown')}")
        print(f"  Stages: {len(pipeline['stages'])}")
        print(f"  Reviews: {len(reviews)}")

        print(f"\n🏗️ INNER PIPELINE:")
        for stage in pipeline["stages"]:
            print(summarize_stage(stage))

        print(f"\n👥 COUNCIL REVIEWS:")
        for review in reviews:
            source = review.get("source", "unknown")
            stance = review.get("stance", "unknown")
            print(f"  • {source}: {stance}")

        print(f"\n💬 FINAL ANSWER (first 200 chars):")
        answer_text = final_answer.get("content", "")[:200]
        print(f"  {answer_text}...")

        print(f"\n✨ SUCCESS!")
        return data

    except httpx.ConnectError:
        print(f"❌ Connection error: Is the server running on {BASE_URL}?")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def run_all_tests():
    """Run all test prompts in sequence."""
    print(f"\n{'#' * 80}")
    print("# COLLABORATE PIPELINE TEST SUITE")
    print(f"{'#' * 80}")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Base URL: {BASE_URL}")
    print(f"Thread ID: {THREAD_ID}")
    print(f"Org ID: {ORG_ID}")

    results = []
    for i, test in enumerate(TEST_PROMPTS, 1):
        result = await test_collaborate(
            message=test["message"],
            test_name=f"{i}. {test['name']}",
        )
        results.append({
            "name": test["name"],
            "success": result is not None,
            "response": result,
        })

        # Wait a bit between tests to avoid rate limiting
        if i < len(TEST_PROMPTS):
            print("\n⏳ Waiting 5s before next test...")
            await asyncio.sleep(5)

    # Summary
    print(f"\n\n{'#' * 80}")
    print("# TEST SUMMARY")
    print(f"{'#' * 80}")
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status}: {result['name']}")

    passed = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")

    return results


def print_response_structure():
    """Print the expected response structure for reference."""
    print(f"\n{'#' * 80}")
    print("# EXPECTED RESPONSE STRUCTURE")
    print(f"{'#' * 80}")
    structure = {
        "final_answer": {
            "content": "<user-facing answer>",
            "model": {
                "provider": "openai",
                "model_slug": "gpt-4o",
                "display_name": "GPT-4o (Director)",
            },
            "created_at": "2025-11-30T...",
            "explanation": {
                "used_internal_report": True,
                "external_reviews_considered": 5,
                "confidence_level": "high",
            },
        },
        "internal_pipeline": {
            "stages": [
                {
                    "id": "stage_analyst_xxx",
                    "role": "analyst",
                    "title": "Analyst",
                    "model": {"provider": "google", "model_slug": "...", "display_name": "..."},
                    "content": "<stage output>",
                    "created_at": "...",
                    "latency_ms": 500,
                },
                "... (researcher, creator, critic, internal_synth)",
            ],
            "compressed_report": {
                "model": {"provider": "...", "model_slug": "...", "display_name": "..."},
                "content": "<compressed summary>",
            },
        },
        "external_reviews": [
            {
                "id": "rev_perplexity_xxx",
                "source": "perplexity",
                "model": {"provider": "perplexity", "model_slug": "...", "display_name": "..."},
                "stance": "agree",
                "content": "Issues:\n- ...\nMissing points:\n- ...",
                "created_at": "...",
                "latency_ms": 800,
            },
            "... (gemini, gpt, kimi, openrouter)",
        ],
        "meta": {
            "run_id": "uuid",
            "mode": "auto",
            "started_at": "...",
            "finished_at": "...",
            "total_latency_ms": 12000,
            "models_involved": [
                {"provider": "google", "model_slug": "...", "display_name": "..."},
                "...",
            ],
        },
    }
    print(format_json(structure))


if __name__ == "__main__":
    print_response_structure()

    # Run all tests
    results = asyncio.run(run_all_tests())

    print(f"\n\n💾 Saving results to test_results.json...")
    with open("test_results.json", "w") as f:
        json.dump(
            [
                {
                    "name": r["name"],
                    "success": r["success"],
                    "has_response": r["response"] is not None,
                }
                for r in results
            ],
            f,
            indent=2,
        )
    print("✅ Saved!")
