import pytest

from app.models.provider_key import ProviderType
from app.services.council.orchestrator import RouterOrchestrator, RouterConfig


class _Resp:
    def __init__(self, content: str):
        self.content = content


@pytest.mark.asyncio
async def test_day1_router_repairs_greeting(monkeypatch):
    calls = []
    outputs = iter(["Hi — here's the answer.", "Here is the answer."])

    async def fake_call_provider_adapter(*, provider, model, messages, api_key, max_tokens=None, **kwargs):
        calls.append({"provider": provider, "model": model, "messages": messages})
        return _Resp(next(outputs))

    monkeypatch.setattr(
        "app.services.council.orchestrator.call_provider_adapter", fake_call_provider_adapter
    )

    orchestrator = RouterOrchestrator()
    out = await orchestrator.run(
        RouterConfig(
            query="Fix the bug in my Python function.",
            api_keys={"openai": "k"},
            thread_id="t1",
        )
    )

    assert out.status == "success"
    assert out.output == "Here is the answer."
    assert out.repaired is True
    assert out.used_fallback is False
    assert len(calls) == 2
    assert calls[0]["provider"] == ProviderType.OPENAI
    assert calls[1]["provider"] == ProviderType.OPENAI


@pytest.mark.asyncio
async def test_day1_router_repairs_forbidden_tokens(monkeypatch):
    calls = []
    outputs = iter(["This is a P0 incident.", "This is a P1 incident."])

    async def fake_call_provider_adapter(*, provider, model, messages, api_key, max_tokens=None, **kwargs):
        calls.append({"provider": provider, "model": model, "messages": messages})
        return _Resp(next(outputs))

    monkeypatch.setattr(
        "app.services.council.orchestrator.call_provider_adapter", fake_call_provider_adapter
    )

    orchestrator = RouterOrchestrator()
    out = await orchestrator.run(
        RouterConfig(
            query="Set incident severity taxonomy and explain how to classify incidents.",
            api_keys={"gemini": "k"},
            thread_id="t2",
        )
    )

    assert out.status == "success"
    assert out.output == "This is a P1 incident."
    assert out.repaired is True
    assert out.used_fallback is False
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_day1_router_fallback_after_failed_repair(monkeypatch):
    calls = []

    async def fake_call_provider_adapter(*, provider, model, messages, api_key, max_tokens=None, **kwargs):
        calls.append(provider)
        # First provider: fails greeting check twice
        if provider == ProviderType.GEMINI:
            return _Resp("Hello! This still greets.")
        # Fallback provider: passes
        return _Resp("Answer without greeting.")

    monkeypatch.setattr(
        "app.services.council.orchestrator.call_provider_adapter", fake_call_provider_adapter
    )

    orchestrator = RouterOrchestrator()
    out = await orchestrator.run(
        RouterConfig(
            query="Summarize the options.",
            api_keys={"gemini": "k", "openai": "k"},
            thread_id="t3",
        )
    )

    assert out.status == "success"
    assert out.output == "Answer without greeting."
    assert out.repaired is True
    assert out.used_fallback is True
    assert calls[0] == ProviderType.GEMINI
    assert calls[1] == ProviderType.GEMINI
    assert calls[2] == ProviderType.OPENAI


@pytest.mark.asyncio
async def test_day1_router_transparent_routing_header(monkeypatch):
    outputs = iter(["Here is the answer."])

    async def fake_call_provider_adapter(*, provider, model, messages, api_key, max_tokens=None, **kwargs):
        return _Resp(next(outputs))

    monkeypatch.setattr(
        "app.services.council.orchestrator.call_provider_adapter", fake_call_provider_adapter
    )

    orchestrator = RouterOrchestrator()
    out = await orchestrator.run(
        RouterConfig(
            query="Fix the bug in my Python function.",
            api_keys={"openai": "k"},
            thread_id="t4",
            transparent_routing=True,
        )
    )

    assert out.status == "success"
    assert out.output.startswith("ROUTING:\n")
    assert "- provider: openai\n" in out.output
    assert "- model: gpt-4o\n" in out.output
