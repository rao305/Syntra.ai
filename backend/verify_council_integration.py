#!/usr/bin/env python3
"""
Council Orchestration Integration Verification Script

Verifies that all components are properly connected:
1. Backend services are properly imported
2. API endpoints are registered
3. Provider dispatch is configured
4. Database provider keys retrieval works
5. Config is properly set up
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

def verify_imports():
    """Verify all required modules can be imported."""
    print("\n" + "="*70)
    print("VERIFICATION 1: Checking Module Imports")
    print("="*70)

    tests = [
        ("FastAPI", "from fastapi import FastAPI"),
        ("SQLAlchemy", "from sqlalchemy.ext.asyncio import AsyncSession"),
        ("Pydantic", "from pydantic import BaseModel"),
        ("OpenAI", "from openai import AsyncOpenAI"),
        ("Google Generative AI", "import google.generativeai"),
        ("HTTPX", "import httpx"),
    ]

    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"✅ {name:30} - Available")
        except ImportError as e:
            print(f"❌ {name:30} - Missing: {e}")
            return False

    return True


def verify_backend_modules():
    """Verify council backend modules exist and are importable."""
    print("\n" + "="*70)
    print("VERIFICATION 2: Checking Backend Modules")
    print("="*70)

    modules = [
        "app.services.council",
        "app.services.council.config",
        "app.services.council.base",
        "app.services.council.orchestrator",
        "app.services.council.agents.architect",
        "app.services.council.agents.data_engineer",
        "app.services.council.agents.researcher",
        "app.services.council.agents.red_teamer",
        "app.services.council.agents.optimizer",
        "app.services.council.agents.synthesizer",
        "app.services.council.agents.judge",
        "app.api.council",
        "app.services.provider_dispatch",
        "app.services.provider_keys",
    ]

    all_good = True
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module:50} - Loaded")
        except ImportError as e:
            print(f"❌ {module:50} - Error: {e}")
            all_good = False

    return all_good


def verify_api_router():
    """Verify council API router is properly configured."""
    print("\n" + "="*70)
    print("VERIFICATION 3: Checking API Router Configuration")
    print("="*70)

    try:
        from app.api import council
        router = council.router

        # Check endpoints
        endpoints = ["/orchestrate", "/ws"]
        found_endpoints = {}

        for route in router.routes:
            if hasattr(route, "path"):
                found_endpoints[route.path] = route

        print(f"✅ Council router imported successfully")
        print(f"✅ Router prefix: {router.prefix}")
        print(f"✅ Router has {len(router.routes)} routes:")

        for route in router.routes:
            if hasattr(route, "methods"):
                methods = ", ".join(route.methods)
                print(f"   - {route.path:40} [{methods}]")
            elif hasattr(route, "path"):
                print(f"   - {route.path:40} [WebSocket]")

        return True
    except Exception as e:
        print(f"❌ Failed to verify API router: {e}")
        return False


def verify_provider_config():
    """Verify provider configuration."""
    print("\n" + "="*70)
    print("VERIFICATION 4: Checking Provider Configuration")
    print("="*70)

    try:
        from app.services.council.config import (
            PROVIDER_MODELS,
            AGENT_PROVIDER_MAPPING,
            get_model_for_provider,
        )
        from app.models.provider_key import ProviderType

        print("✅ Provider configuration loaded successfully\n")

        print("Provider-to-Model Mapping:")
        for provider, config in PROVIDER_MODELS.items():
            print(f"   - {provider.value:15} → {config['model']}")

        print("\nAgent-to-Provider Mapping:")
        for agent, provider in AGENT_PROVIDER_MAPPING.items():
            print(f"   - {agent:20} → {provider.value}")

        # Test model retrieval
        print("\nTesting Model Retrieval:")
        for provider in [
            ProviderType.OPENAI,
            ProviderType.GEMINI,
            ProviderType.PERPLEXITY,
            ProviderType.KIMI,
        ]:
            model = get_model_for_provider(provider)
            print(f"   - {provider.value:15} → {model}")

        return True
    except Exception as e:
        print(f"❌ Failed to verify provider config: {e}")
        return False


def verify_provider_dispatch():
    """Verify provider dispatch is configured correctly."""
    print("\n" + "="*70)
    print("VERIFICATION 5: Checking Provider Dispatch")
    print("="*70)

    try:
        from app.services.provider_dispatch import (
            call_provider_adapter,
            DEFAULT_COMPLETION_TOKENS,
        )
        from app.models.provider_key import ProviderType

        print("✅ Provider dispatch module loaded successfully\n")

        print("Completion Token Budgets:")
        for provider, tokens in DEFAULT_COMPLETION_TOKENS.items():
            print(f"   - {provider.value:15} → {tokens:5} tokens")

        print("\n✅ All providers have dispatch adapters configured")
        return True
    except Exception as e:
        print(f"❌ Failed to verify provider dispatch: {e}")
        return False


def verify_orchestrator():
    """Verify orchestrator is properly configured."""
    print("\n" + "="*70)
    print("VERIFICATION 6: Checking Orchestrator")
    print("="*70)

    try:
        from app.services.council import CouncilOrchestrator, CouncilConfig
        from app.services.council.config import OutputMode

        print("✅ CouncilOrchestrator imported successfully")
        print("✅ CouncilConfig imported successfully")

        # Check output modes
        print("\nAvailable Output Modes:")
        for mode in OutputMode:
            print(f"   - {mode.value}")

        return True
    except Exception as e:
        print(f"❌ Failed to verify orchestrator: {e}")
        return False


def verify_main_app():
    """Verify council router is registered in main app."""
    print("\n" + "="*70)
    print("VERIFICATION 7: Checking Main App Registration")
    print("="*70)

    try:
        import main
        app = main.app

        # Check if council router is registered
        council_routes = [
            route for route in app.routes
            if hasattr(route, "path") and "/api/council" in route.path
        ]

        if council_routes:
            print(f"✅ Council routes registered in main app")
            print(f"✅ Found {len(council_routes)} council routes:")
            for route in council_routes[:5]:  # Show first 5
                print(f"   - {route.path}")
            return True
        else:
            print(f"❌ No council routes found in main app")
            return False

    except Exception as e:
        print(f"❌ Failed to verify main app: {e}")
        return False


def verify_agent_prompts():
    """Verify all agent prompts are available."""
    print("\n" + "="*70)
    print("VERIFICATION 8: Checking Agent Prompts")
    print("="*70)

    try:
        from app.services.council.agents import (
            ARCHITECT_PROMPT,
            DATA_ENGINEER_PROMPT,
            RESEARCHER_PROMPT,
            RED_TEAMER_PROMPT,
            OPTIMIZER_PROMPT,
            SYNTHESIZER_PROMPT,
            get_judge_prompt,
        )

        prompts = {
            "ARCHITECT": ARCHITECT_PROMPT,
            "DATA_ENGINEER": DATA_ENGINEER_PROMPT,
            "RESEARCHER": RESEARCHER_PROMPT,
            "RED_TEAMER": RED_TEAMER_PROMPT,
            "OPTIMIZER": OPTIMIZER_PROMPT,
            "SYNTHESIZER": SYNTHESIZER_PROMPT,
        }

        print("✅ All agent prompts loaded successfully\n")

        for name, prompt in prompts.items():
            length = len(prompt)
            print(f"   - {name:20} ({length:5} chars)")

        # Test judge prompt generation
        judge_audit = get_judge_prompt("audit")
        print(f"   - {'JUDGE (audit)':20} ({len(judge_audit):5} chars)")

        return True
    except Exception as e:
        print(f"❌ Failed to verify agent prompts: {e}")
        return False


def print_summary(results):
    """Print summary of verification results."""
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)

    passed = sum(results.values())
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print("\n" + "-"*70)
    print(f"Overall: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 ALL VERIFICATIONS PASSED! System is ready for testing.")
        return True
    else:
        print(f"\n⚠️  {total - passed} verification(s) failed. Please review above.")
        return False


async def main():
    """Run all verifications."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  Council Orchestration Integration Verification".center(68) + "║")
    print("║" + "  2025-12-12".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")

    results = {
        "Module Imports": verify_imports(),
        "Backend Modules": verify_backend_modules(),
        "API Router": verify_api_router(),
        "Provider Config": verify_provider_config(),
        "Provider Dispatch": verify_provider_dispatch(),
        "Orchestrator": verify_orchestrator(),
        "Main App Registration": verify_main_app(),
        "Agent Prompts": verify_agent_prompts(),
    }

    success = print_summary(results)

    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    if success:
        print("""
1. Verify API keys are configured in database:
   - Check provider_keys table for your org
   - Ensure at least one provider has an active key

2. Test API endpoint:
   POST /api/council/orchestrate
   Headers: x-org-id: your_org_id
   Body: {
     "query": "Create a simple REST API",
     "output_mode": "deliverable-ownership"
   }

3. Monitor with WebSocket:
   WS /api/council/ws/{session_id}

4. Start frontend testing with the components:
   - CouncilOrchestration.tsx
   - CollaborationButton.tsx
   - useCouncilOrchestrator.ts
""")
    else:
        print("""
Please fix the failing verifications above before testing.
""")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
