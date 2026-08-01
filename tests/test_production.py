from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.config import Settings
from services.observability.logging_setup import (
    JsonFormatter,
    clear_correlation_id,
    get_correlation_id,
    set_correlation_id,
)


def _prod_settings(tmp_path: Path, **overrides: object) -> Settings:
    base = {
        "env": "prod",
        "api_token": "secret-token",
        "require_api_token": True,
        "trusted_hosts_raw": "127.0.0.1,localhost,testserver",
        "qdrant_url": "http://localhost:6333",
        "runtime_log_path": tmp_path / "agent.log",
        "audit_log_path": tmp_path / "audit.jsonl",
        "task_store_path": tmp_path / "tasks.json",
        "memory_store_path": tmp_path / "memory.json",
        "backup_dir": tmp_path / "backups",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_prod_guard_requires_token() -> None:
    settings = Settings(
        env="prod",
        require_api_token=True,
        api_token=None,
    )
    with pytest.raises(ValueError, match="API_TOKEN"):
        settings.validate_production_guards()


def test_prod_guard_allows_dev_without_token() -> None:
    settings = Settings(env="dev", require_api_token=True, api_token=None)
    settings.validate_production_guards()


def test_ready_and_health_endpoints(tmp_path: Path) -> None:
    settings = _prod_settings(tmp_path, env="dev", require_api_token=False, api_token=None)
    with patch("apps.api.main.load_settings", return_value=settings):
        client = TestClient(create_app())
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert "version" in health.json()
    ready = client.get("/ready")
    assert ready.status_code == 200
    payload = ready.json()
    assert payload["memory_ok"] is True
    assert "ollama_ok" in payload
    assert "bind_host" in payload


def test_api_token_protects_mutating_routes(tmp_path: Path) -> None:
    settings = _prod_settings(tmp_path, env="dev")
    with patch("apps.api.main.load_settings", return_value=settings):
        client = TestClient(create_app())

    denied = client.post("/memory", json={"kind": "fact", "key": "k", "value": "v"})
    assert denied.status_code == 401

    allowed = client.post(
        "/memory",
        json={"kind": "fact", "key": "k", "value": "v"},
        headers={"X-API-Token": "secret-token"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["key"] == "k"

    bearer = client.post(
        "/memory",
        json={"kind": "fact", "key": "k2", "value": "v2"},
        headers={"Authorization": "Bearer secret-token"},
    )
    assert bearer.status_code == 200


def test_get_routes_remain_open_with_token_configured(tmp_path: Path) -> None:
    settings = _prod_settings(tmp_path, env="dev")
    with patch("apps.api.main.load_settings", return_value=settings):
        client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/status").status_code == 200


def test_correlation_id_context_and_json_formatter() -> None:
    clear_correlation_id()
    assert get_correlation_id() is None
    set_correlation_id("cid-123")
    assert get_correlation_id() == "cid-123"
    record = __import__("logging").LogRecord(
        name="test",
        level=20,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "cid-123"
    line = JsonFormatter().format(record)
    assert '"correlation_id": "cid-123"' in line
    assert '"message": "hello"' in line
    clear_correlation_id()


def test_compose_binds_localhost() -> None:
    compose = Path("infra/docker-compose.yml").read_text(encoding="utf-8")
    assert "127.0.0.1:8000:8000" in compose
    assert "127.0.0.1:6333:6333" in compose
    assert "restart: unless-stopped" in compose
    assert "condition: service_healthy" in compose


def test_dockerfile_runs_as_non_root() -> None:
    dockerfile = Path("infra/api.Dockerfile").read_text(encoding="utf-8")
    assert "USER appuser" in dockerfile
    assert "useradd" in dockerfile
