from app.services.routing_header import RoutingHeaderInfo, build_routing_header, provider_name
from app.models.provider_key import ProviderType


def test_provider_name_normalization():
    assert provider_name(ProviderType.OPENAI) == "openai"
    assert provider_name(ProviderType.GEMINI) == "google"
    assert provider_name("Gemini") == "google"
    assert provider_name(None) == "unknown"


def test_build_routing_header_exact_shape():
    header = build_routing_header(
        RoutingHeaderInfo(
            provider="openai",
            model="gpt-4o-mini",
            route_reason="Deep context + structured policy output",
            context="full_history",
            repair_attempts=1,
            fallback_used="yes",
        )
    )

    lines = header.strip("\n").split("\n")
    assert len(lines) == 7  # "ROUTING:" + 6 fields
    assert lines[0] == "ROUTING:"
    assert lines[1].startswith("- provider: ")
    assert lines[2].startswith("- model: ")
    assert lines[3].startswith("- route_reason: ")
    assert lines[4].startswith("- context: ")
    assert lines[5] == "- repair_attempts: 1"
    assert lines[6] == "- fallback_used: yes"

