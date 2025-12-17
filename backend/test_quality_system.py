"""
Test script for the quality validation system.

Tests:
1. Query complexity classification
2. Quality directive injection
3. Quality validation scoring
4. End-to-end council with quality validation
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.services.council.query_classifier import (
    classify_query,
    classify_query_heuristic,
    QueryComplexity
)
from app.services.council.quality_directive import (
    QUALITY_DIRECTIVE,
    get_role_specific_directive,
    inject_quality_directive
)
from app.services.council.quality_validator import (
    validate_response_quality,
    analyze_response_heuristics,
    check_code_quality,
    check_citations
)
from app.services.council.orchestrator import (
    CouncilOrchestrator,
    CouncilConfig,
    OutputMode
)


# Test queries of different complexity levels
TEST_QUERIES = {
    "level_1": "What is the capital of France?",
    "level_2": "How does gradient descent work?",
    "level_3": "Write a function to detect cycles in a linked list",
    "level_4": "Compare transformer architectures for time series forecasting",
    "level_5": "Prove convergence properties of overparameterized neural networks using Neural Tangent Kernel theory"
}

# Test responses with varying quality
TEST_RESPONSES = {
    "good_response": """
# Complete Implementation

Here's a complete implementation of cycle detection in a linked list using Floyd's cycle detection algorithm:

```python
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def has_cycle(head: ListNode) -> bool:
    \"\"\"
    Detect if a linked list has a cycle using Floyd's algorithm.

    Time Complexity: O(n)
    Space Complexity: O(1)

    Args:
        head: Head of the linked list

    Returns:
        True if cycle exists, False otherwise
    \"\"\"
    if not head or not head.next:
        return False

    slow = head
    fast = head.next

    while slow != fast:
        if not fast or not fast.next:
            return False
        slow = slow.next
        fast = fast.next.next

    return True

# Test cases
def test_has_cycle():
    # Test 1: No cycle
    node1 = ListNode(1)
    node2 = ListNode(2)
    node3 = ListNode(3)
    node1.next = node2
    node2.next = node3
    assert has_cycle(node1) == False

    # Test 2: Cycle exists
    node1 = ListNode(1)
    node2 = ListNode(2)
    node3 = ListNode(3)
    node1.next = node2
    node2.next = node3
    node3.next = node1  # Create cycle
    assert has_cycle(node1) == True

    # Test 3: Empty list
    assert has_cycle(None) == False

    print("All tests passed!")

if __name__ == "__main__":
    test_has_cycle()
```

## Algorithm Explanation

The Floyd's cycle detection algorithm (also known as "tortoise and hare") uses two pointers:
- **Slow pointer**: Moves one step at a time
- **Fast pointer**: Moves two steps at a time

If there's a cycle, the fast pointer will eventually catch up to the slow pointer.

## Time and Space Complexity

- **Time Complexity**: O(n) where n is the number of nodes
- **Space Complexity**: O(1) - only uses two pointers

## Edge Cases Handled

1. Empty list (head is None)
2. Single node with no cycle
3. Cycle at the beginning
4. Cycle in the middle
5. Cycle at the end
""",
    "bad_response": """
## Solution

✅ Task: Detect cycle in linked list
✅ Owner: Developer
✅ Status: Complete

### File Structure
- main.py
- test.py
- config.py

### Code

```python
def detect_cycle(head):
    # TODO: Implement cycle detection
    pass
```

### Next Steps
- Implement the function
- Add test cases
- Review edge cases
""",
    "mediocre_response": """
Here's how to detect cycles:

```python
def has_cycle(head):
    slow = head
    fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            return True
    return False
```

This uses Floyd's algorithm.
"""
}


async def test_query_classification():
    """Test query complexity classification."""
    print("\n" + "="*80)
    print("TEST 1: Query Complexity Classification")
    print("="*80)

    # Get API keys from environment
    api_keys = {
        "openai": os.getenv("OPENAI_API_KEY"),
    }

    for level_name, query in TEST_QUERIES.items():
        print(f"\n{level_name.upper()}: {query}")

        # Heuristic classification
        heuristic_level = classify_query_heuristic(query)
        print(f"  Heuristic: Level {heuristic_level}")

        # LLM classification (if API key available)
        if api_keys.get("openai"):
            llm_level, reasoning = await classify_query(query, api_keys, use_llm=True)
            print(f"  LLM: Level {llm_level} - {reasoning}")

    print("\n✅ Query classification test complete")


async def test_quality_directive_injection():
    """Test quality directive injection."""
    print("\n" + "="*80)
    print("TEST 2: Quality Directive Injection")
    print("="*80)

    roles = ["analyst", "researcher", "creator", "critic", "synthesizer", "judge"]

    for role in roles:
        print(f"\n{role.upper()} directive:")
        directive = get_role_specific_directive(role)
        print(directive[:200] + "..." if len(directive) > 200 else directive)

    # Test full injection
    test_prompt = "You are a helpful assistant."
    enhanced_prompt = inject_quality_directive(
        agent_prompt=test_prompt,
        role="creator",
        query_complexity=5
    )

    print(f"\n\nFull enhanced prompt length: {len(enhanced_prompt)} chars")
    print(f"Contains QUALITY_DIRECTIVE: {'QUALITY_DIRECTIVE' in enhanced_prompt}")
    print(f"Contains role-specific directive: {'CREATOR AGENT' in enhanced_prompt}")

    print("\n✅ Quality directive injection test complete")


async def test_response_validation():
    """Test response quality validation."""
    print("\n" + "="*80)
    print("TEST 3: Response Quality Validation")
    print("="*80)

    api_keys = {
        "openai": os.getenv("OPENAI_API_KEY"),
    }

    if not api_keys.get("openai"):
        print("⚠️  Skipping (no OpenAI API key)")
        return

    query = TEST_QUERIES["level_3"]  # Linked list cycle detection

    for response_name, response in TEST_RESPONSES.items():
        print(f"\n{response_name.upper()}:")
        print("-" * 40)

        # Heuristic analysis
        heuristics = analyze_response_heuristics(response, query_complexity=3)
        print(f"Heuristics:")
        print(f"  Substance score: {heuristics['substance_score_heuristic']:.1f}")
        print(f"  Depth score: {heuristics['depth_score_heuristic']:.1f}")
        print(f"  Placeholder count: {heuristics['placeholder_count']}")
        print(f"  Code blocks: {heuristics['code_block_count']}")
        print(f"  Word count: {heuristics['word_count']}")

        # Code quality check
        code_passes, code_issues = check_code_quality(response)
        print(f"Code quality: {'✅ Pass' if code_passes else '❌ Fail'}")
        if code_issues:
            for issue in code_issues:
                print(f"    - {issue}")

        # LLM validation (only for good_response to save API calls)
        if response_name == "good_response":
            print("\nRunning LLM validation...")
            validation_result = await validate_response_quality(
                query=query,
                response=response,
                query_complexity=3,
                api_keys=api_keys
            )

            scores = validation_result.scores
            print(f"LLM Scores:")
            print(f"  Substance: {scores.substance_score:.1f}/10")
            print(f"  Completeness: {scores.completeness_score:.1f}/10")
            print(f"  Depth: {scores.depth_score:.1f}/10")
            print(f"  Accuracy: {scores.accuracy_score:.1f}/10")
            print(f"  Overall: {scores.overall_score:.1f}/10")
            print(f"  Quality gate: {'✅ PASSED' if scores.quality_gate_passed else '❌ FAILED'}")

            if validation_result.gaps_identified:
                print(f"Gaps identified: {', '.join(validation_result.gaps_identified)}")

    print("\n✅ Response validation test complete")


async def test_end_to_end_council():
    """Test end-to-end council with quality validation."""
    print("\n" + "="*80)
    print("TEST 4: End-to-End Council with Quality Validation")
    print("="*80)

    # Get API keys from environment
    api_keys = {
        "openai": os.getenv("OPENAI_API_KEY"),
        "gemini": os.getenv("GEMINI_API_KEY"),
        "perplexity": os.getenv("PERPLEXITY_API_KEY"),
    }

    # Filter out None keys
    api_keys = {k: v for k, v in api_keys.items() if v}

    if not api_keys:
        print("⚠️  Skipping (no API keys available)")
        return

    print(f"Available API keys: {list(api_keys.keys())}")

    # Use a simple query for testing
    query = "Write a Python function to calculate factorial recursively with proper error handling"

    config = CouncilConfig(
        query=query,
        output_mode=OutputMode.DELIVERABLE_ONLY,
        api_keys=api_keys,
        verbose=True,
        enable_quality_directive=True,
        enable_quality_validation=True,
        query_complexity=3  # Technical implementation
    )

    orchestrator = CouncilOrchestrator()

    print(f"\nRunning council for query: {query}")
    print("This may take a few minutes...\n")

    # Progress callback to track stages
    async def progress_cb(event):
        event_type = event.get("type")
        if event_type == "agent_start":
            print(f"  🔄 Starting: {event.get('agent')}")
        elif event_type == "agent_complete":
            agent = event.get('agent')
            status = event.get('status', 'success')
            if status == 'success':
                output_len = len(event.get('output', ''))
                print(f"  ✅ Completed: {agent} ({output_len} chars)")
                # Show quality scores if available
                if 'scores' in event:
                    scores = event['scores']
                    print(f"     Quality: {scores.get('overall_score', 0):.1f}/10")
            else:
                print(f"  ❌ Failed: {agent}")
        elif event_type == "phase_start":
            print(f"\n{'='*60}")
            print(f"  {event.get('message', event.get('phase'))}")
            print(f"{'='*60}")

    try:
        result = await orchestrator.run(config, progress_callback=progress_cb)

        if result.status == "success":
            print("\n" + "="*80)
            print("COUNCIL COMPLETED SUCCESSFULLY")
            print("="*80)
            print(f"\nExecution time: {result.execution_time_ms}ms")
            print(f"\nFinal output length: {len(result.output)} chars")
            print("\nFirst 500 chars of output:")
            print("-" * 40)
            print(result.output[:500])
            print("...")
        else:
            print(f"\n❌ Council failed: {result.error}")

    except Exception as e:
        print(f"\n❌ Council error: {e}")
        import traceback
        traceback.print_exc()

    print("\n✅ End-to-end test complete")


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("QUALITY VALIDATION SYSTEM TEST SUITE")
    print("="*80)

    # Check for API keys
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    has_perplexity = bool(os.getenv("PERPLEXITY_API_KEY"))

    print(f"\nAPI Keys Available:")
    print(f"  OpenAI: {'✅' if has_openai else '❌'}")
    print(f"  Gemini: {'✅' if has_gemini else '❌'}")
    print(f"  Perplexity: {'✅' if has_perplexity else '❌'}")

    if not any([has_openai, has_gemini, has_perplexity]):
        print("\n⚠️  Warning: No API keys found. Some tests will be skipped.")
        print("Set OPENAI_API_KEY, GEMINI_API_KEY, or PERPLEXITY_API_KEY environment variables.")

    # Run tests
    await test_query_classification()
    await test_quality_directive_injection()
    await test_response_validation()

    # End-to-end test (optional, can be slow/expensive)
    run_e2e = input("\n\nRun end-to-end council test? (y/n): ").strip().lower() == 'y'
    if run_e2e:
        await test_end_to_end_council()
    else:
        print("\nSkipping end-to-end test")

    print("\n" + "="*80)
    print("ALL TESTS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
