#!/usr/bin/env python3
"""
Run golden tests through the collaboration system and collect results.

This script:
1. Loads golden test cases
2. Runs each test through the collaboration API
3. Collects transcripts with routing, repair attempts, etc.
4. Outputs results in format expected by evaluation API
"""

import json
import os
import sys
import time
import requests
from datetime import datetime
from typing import Dict, List, Any

API_URL = os.getenv("API_URL", "http://localhost:8000")
ORG_ID = os.getenv("ORG_ID", "org_demo")
GOLDEN_TESTS_FILE = os.getenv("GOLDEN_TESTS_FILE", "backend/tests/examples/golden_tests_example.json")


def run_collaboration_test(test: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a single test through the collaboration system.
    
    Returns transcript with run_id, routing, final_output, etc.
    """
    run_id = f"run_{int(time.time())}_{test['test_id']}"
    
    # Prepare collaboration request
    collab_request = {
        "query": test["user_prompt"],
        "output_mode": "deliverable-ownership",
        "context_pack": {
            "locked_decisions": test.get("expected_output_contract", {}).get("locked_decisions", []),
            "open_questions": []
        },
        "lexicon_lock": test.get("lexicon_lock"),
        "output_contract": test.get("expected_output_contract"),
        "transparency_mode": False
    }
    
    print(f"Running test {test['test_id']}: {test['title']}...", file=sys.stderr)
    
    try:
        # Start collaboration
        response = requests.post(
            f"{API_URL}/api/council/orchestrate",
            headers={
                "Content-Type": "application/json",
                "x-org-id": ORG_ID
            },
            json={
                "query": test["user_prompt"],
                "output_mode": "deliverable-ownership",
                "lexicon_lock": test.get("lexicon_lock"),
                "output_contract": test.get("expected_output_contract"),
                "transparency_mode": False
            },
            timeout=300  # 5 minutes per test
        )
        
        if response.status_code != 200:
            print(f"ERROR: Collaboration API returned {response.status_code}", file=sys.stderr)
            return {
                "run_id": run_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "final_output": f"ERROR: API returned {response.status_code}",
                "repair_attempts": 0,
                "fallback_used": False
            }
        
        session_data = response.json()
        session_id = session_data["session_id"]
        
        # Poll for completion (or use WebSocket in future)
        max_wait = 600  # 10 minutes max
        wait_time = 0
        poll_interval = 5
        
        while wait_time < max_wait:
            status_response = requests.get(
                f"{API_URL}/api/council/orchestrate/{session_id}",
                headers={"x-org-id": ORG_ID},
                timeout=30
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                if status_data["status"] == "success":
                    # Get final output
                    final_output = status_data.get("output", "")
                    
                    # Extract routing info from session (if available)
                    routing = None  # Could be extracted from session metadata
                    
                    return {
                        "run_id": run_id,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "thread_id": session_id,
                        "routing": routing,
                        "repair_attempts": 0,  # Could track from session
                        "fallback_used": False,  # Could track from session
                        "final_output": final_output
                    }
                elif status_data["status"] == "error":
                    return {
                        "run_id": run_id,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "thread_id": session_id,
                        "final_output": f"ERROR: {status_data.get('error', 'Unknown error')}",
                        "repair_attempts": 0,
                        "fallback_used": False
                    }
            
            time.sleep(poll_interval)
            wait_time += poll_interval
        
        # Timeout
        return {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "thread_id": session_id,
            "final_output": "ERROR: Timeout waiting for completion",
            "repair_attempts": 0,
            "fallback_used": False
        }
        
    except Exception as e:
        print(f"ERROR running test {test['test_id']}: {e}", file=sys.stderr)
        return {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "final_output": f"ERROR: {str(e)}",
            "repair_attempts": 0,
            "fallback_used": False
        }


def main():
    """Main entry point."""
    # Load golden tests
    with open(GOLDEN_TESTS_FILE, 'r') as f:
        data = json.load(f)
    
    tests = data.get("tests", [])
    
    if not tests:
        print("ERROR: No tests found in golden tests file", file=sys.stderr)
        sys.exit(1)
    
    print(f"Running {len(tests)} golden tests...", file=sys.stderr)
    
    # Run each test
    transcripts = []
    for test in tests:
        transcript = run_collaboration_test(test)
        transcripts.append(transcript)
        time.sleep(2)  # Small delay between tests
    
    # Prepare evaluation request
    eval_request = {
        "tests": [
            {
                "test_id": t["test_id"],
                "title": t["title"],
                "user_prompt": t["user_prompt"],
                "expected_output_contract": t.get("expected_output_contract", {}),
                "lexicon_lock": t.get("lexicon_lock"),
                "domain_checklist": t.get("domain_checklist"),
                "priority": t.get("priority", "P2")
            }
            for t in tests
        ],
        "transcripts": transcripts,
        "run_metadata": {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "build_commit": os.getenv("GITHUB_SHA", "local"),
            "environment": "github-actions",
            "providers_enabled": ["openai", "gemini", "perplexity", "kimi"],
            "notes": "Nightly evaluation run"
        }
    }
    
    # Output JSON for evaluation API
    print(json.dumps(eval_request, indent=2))


if __name__ == "__main__":
    main()

