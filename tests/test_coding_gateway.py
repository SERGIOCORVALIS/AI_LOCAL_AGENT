from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from apps.coding.main import create_app
from services.integrations.coding_agents import CodingAgentsAdapter


def test_coding_gateway_health_and_agents(tmp_path: Path) -> None:
    which = MagicMock(side_effect=lambda name: f"/bin/{name}" if name != "claude" else None)
    adapter = CodingAgentsAdapter(
        enabled=True,
        default_agent="auto",
        model="gemma4",
        which=which,
    )
    client = TestClient(create_app(adapter=adapter))

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["service"] == "coding"

    agents = client.get("/agents")
    assert agents.status_code == 200
    body = agents.json()
    assert body["runtime"] == "docker-sidecar"
    assert "codex" in body["available"]
    assert body["agents"]["claude"]["installed"] is False


def test_coding_gateway_run_with_fake_runner(tmp_path: Path) -> None:
    runner = MagicMock(
        return_value=SimpleNamespace(returncode=0, stdout="sidecar ran", stderr="")
    )
    which = MagicMock(return_value="/bin/codex")
    adapter = CodingAgentsAdapter(
        enabled=True,
        default_agent="codex",
        model="gemma4",
        which=which,
        runner=runner,
    )
    client = TestClient(create_app(adapter=adapter))
    response = client.post(
        "/run",
        json={"prompt": "implement helper", "agent": "codex", "cwd": str(tmp_path)},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["stdout"] == "sidecar ran"
    runner.assert_called_once()


def test_coding_gateway_run_missing_cli() -> None:
    adapter = CodingAgentsAdapter(
        enabled=True,
        which=MagicMock(return_value=None),
    )
    client = TestClient(create_app(adapter=adapter))
    response = client.post("/run", json={"prompt": "implement helper"})
    assert response.status_code == 503
