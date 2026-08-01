from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import httpx

from packages.config import Settings
from services.llm import OLLAMA_UNAVAILABLE, OllamaClient


def test_ollama_client_returns_unavailable_marker_when_down() -> None:
    client = OllamaClient(base_url="http://127.0.0.1:9", timeout=0.5)
    assert client.ping() is False
    assert client.list_models() == []
    assert client.generate("model", "hello") == OLLAMA_UNAVAILABLE
    assert client.chat("model", [{"role": "user", "content": "hi"}]) == OLLAMA_UNAVAILABLE


def test_ollama_client_list_models() -> None:
    mock_client = MagicMock()
    tags = MagicMock()
    tags.raise_for_status = MagicMock()
    tags.json.return_value = {"models": [{"name": "gemma:latest"}, {"name": "nomic-embed-text"}]}
    mock_client.get.return_value = tags
    client = OllamaClient(base_url="http://example.local", client=mock_client)
    assert client.list_models() == ["gemma:latest", "nomic-embed-text"]


def test_ollama_client_generate_and_chat_success() -> None:
    mock_client = MagicMock()
    tags = MagicMock()
    tags.is_success = True
    generate = MagicMock()
    generate.raise_for_status = MagicMock()
    generate.json.return_value = {"response": "generated text"}
    chat = MagicMock()
    chat.raise_for_status = MagicMock()
    chat.json.return_value = {"message": {"content": "chat text"}}
    mock_client.get.return_value = tags
    mock_client.post.side_effect = [generate, chat]

    client = OllamaClient(base_url="http://example.local", client=mock_client)
    assert client.ping() is True
    assert client.generate("m", "p") == "generated text"
    assert client.chat("m", [{"role": "user", "content": "hi"}]) == "chat text"


def test_ollama_client_chat_json_parses_payload() -> None:
    mock_client = MagicMock()
    tags = MagicMock()
    tags.is_success = True
    chat = MagicMock()
    chat.raise_for_status = MagicMock()
    content = 'prefix {"tier":"complex","assigned_roles":["ops"]} trailing'
    chat.json.return_value = {"message": {"content": content}}
    mock_client.get.return_value = tags
    mock_client.post.return_value = chat
    client = OllamaClient(base_url="http://example.local", client=mock_client)
    payload = client.chat_json("m", "confirm")
    assert payload == {"tier": "complex", "assigned_roles": ["ops"]}


def test_ollama_client_generate_with_image(tmp_path: Path) -> None:
    image = tmp_path / "x.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 20)
    mock_client = MagicMock()
    tags = MagicMock()
    tags.is_success = True
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"response": "a button"}
    mock_client.get.return_value = tags
    mock_client.post.return_value = response
    client = OllamaClient(base_url="http://example.local", client=mock_client)
    assert client.generate_with_image("vision", "describe", image) == "a button"


def test_ollama_client_handles_http_errors() -> None:
    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.ConnectError("down")
    client = OllamaClient(base_url="http://example.local", client=mock_client)
    assert client.ping() is False


def test_ollama_client_embed_success() -> None:
    mock_client = MagicMock()
    tags = MagicMock()
    tags.is_success = True
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
    mock_client.get.return_value = tags
    mock_client.post.return_value = response
    client = OllamaClient(base_url="http://example.local", client=mock_client)
    assert client.embed("nomic-embed-text", "hello") == [0.1, 0.2, 0.3]


def test_settings_include_ollama_fields() -> None:
    settings = Settings()
    assert settings.ollama_url.startswith("http")
    assert settings.model_vision
    assert settings.model_embed
    assert settings.sandbox_prefer_docker is True
    assert "format_disk" in settings.denied_execute_actions
