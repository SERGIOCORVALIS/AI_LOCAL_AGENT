"""Optional live Ollama checks — skipped when the daemon is unreachable."""

from __future__ import annotations

import os

import pytest

from packages.config import Settings
from services.llm import OLLAMA_UNAVAILABLE, OllamaClient


def _live_client() -> OllamaClient:
    settings = Settings()
    url = os.environ.get("LOCAL_AI_AGENT_OLLAMA_URL", settings.ollama_url)
    return OllamaClient(base_url=url, timeout=5.0)


@pytest.mark.integration
def test_live_ollama_generate_when_available() -> None:
    client = _live_client()
    if not client.ping():
        pytest.skip("Ollama daemon is not reachable")
    settings = Settings()
    text = client.generate(settings.model_primary, "Reply with the single word: pong")
    assert text != OLLAMA_UNAVAILABLE
    assert text.strip()


@pytest.mark.integration
def test_live_ollama_embed_when_available() -> None:
    client = _live_client()
    if not client.ping():
        pytest.skip("Ollama daemon is not reachable")
    settings = Settings()
    vector = client.embed(settings.model_embed, "local memory semantic probe")
    if vector is None:
        pytest.skip(f"Embedding model '{settings.model_embed}' is not available")
    assert len(vector) > 8
