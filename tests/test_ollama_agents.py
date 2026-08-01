from __future__ import annotations

from unittest.mock import MagicMock

from services.llm import (
    AgentModelConfig,
    OllamaClient,
    agents_from_settings,
    ollama_agents_readiness,
    resolve_agents,
    resolve_model_name,
)


def test_resolve_model_name_matches_family_and_tags() -> None:
    from services.llm.models import model_is_available, model_matches

    installed = ["gemma4:e4b-it-q4_K_M", "nomic-embed-text:latest", "dimavz/whisper-tiny:latest"]
    assert resolve_model_name("gemma4", installed) == "gemma4:e4b-it-q4_K_M"
    assert resolve_model_name("gemma4:e4b-it-q4_K_M", installed) == "gemma4:e4b-it-q4_K_M"
    assert resolve_model_name("nomic-embed-text", installed) == "nomic-embed-text:latest"
    assert resolve_model_name("missing-model", installed) is None
    assert resolve_model_name("", installed) is None
    assert model_matches("gemma4", "gemma4:e4b-it-q4_K_M") is True
    assert model_matches("gemma4:other", "gemma4:e4b-it-q4_K_M") is False
    assert model_is_available("gemma4", installed) is True
    # Soft family match when prefix/exact paths do not apply.
    soft = resolve_model_name("whisper", ["dimavz/whisper-tiny:latest"])
    assert soft == "dimavz/whisper-tiny:latest"


def test_agent_model_config_role_mapping() -> None:
    agents = AgentModelConfig(
        primary="gemma4:chat",
        router="gemma4:fast",
        vision="gemma4:chat",
        embed="nomic-embed-text",
    )
    assert agents.for_role("coder") == "gemma4:chat"
    assert agents.for_role("reviewer") == "gemma4:chat"
    assert agents.for_role("router") == "gemma4:fast"
    assert agents.for_role("ops") == "gemma4:fast"
    assert agents.for_route_target("tooling-fastpath") == "gemma4:fast"
    assert agents.for_route_target("gemma4:chat") == "gemma4:chat"


def test_resolve_agents_against_installed_tags() -> None:
    client = MagicMock(spec=OllamaClient)
    client.ping.return_value = True
    client.list_models.return_value = ["gemma4:e4b-it-q4_K_M", "nomic-embed-text:latest"]
    configured = agents_from_settings(
        primary="gemma4",
        router="gemma4",
        vision="gemma4",
        embed="nomic-embed-text",
    )
    resolved = resolve_agents(client, configured)
    assert resolved.online is True
    assert resolved.resolved.primary == "gemma4:e4b-it-q4_K_M"
    assert resolved.resolved.embed == "nomic-embed-text:latest"


def test_ollama_agents_readiness_reports_missing_models() -> None:
    client = MagicMock(spec=OllamaClient)
    client.ping.return_value = True
    client.list_models.return_value = ["nomic-embed-text:latest"]
    agents = AgentModelConfig(
        primary="gemma4",
        router="gemma4",
        vision="gemma4",
        embed="nomic-embed-text",
    )
    payload = ollama_agents_readiness(client, agents)
    assert payload["online"] is True
    assert payload["slots"]["embed"]["available"] is True
    assert payload["slots"]["primary"]["available"] is False
    assert payload["all_required_available"] is False
    assert "coder" in payload["roles"]
    assert payload["roles"]["router"]["slot"] == "router"


def test_ollama_client_resolve_and_has_model() -> None:
    mock_client = MagicMock()
    tags = MagicMock()
    tags.raise_for_status = MagicMock()
    tags.is_success = True
    tags.json.return_value = {"models": [{"name": "gemma4:e4b-it-q4_K_M"}]}
    mock_client.get.return_value = tags
    client = OllamaClient(base_url="http://example.local", client=mock_client)
    assert client.resolve_model("gemma4") == "gemma4:e4b-it-q4_K_M"
    assert client.has_model("gemma4") is True
    assert client.has_model("missing") is False
