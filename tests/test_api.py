from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from apps.api.main import app, create_app
from packages.config import Settings


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    base: dict[str, object] = {
        "api_token": None,
        "require_api_token": False,
        "downloads_watch_path": tmp_path,
        "runtime_log_path": tmp_path / "agent.log",
        "audit_log_path": tmp_path / "events.jsonl",
        "task_store_path": tmp_path / "state.json",
        "memory_store_path": tmp_path / "preferences.json",
        "backup_dir": tmp_path / "backups",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def _client(tmp_path: Path, **overrides: object) -> TestClient:
    settings = _settings(tmp_path, **overrides)
    with patch("apps.api.main.load_settings", return_value=settings):
        return TestClient(create_app())


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_run_task_endpoint(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/tasks/run",
        json={"title": "API", "goal": "Exercise API runtime"},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_status_endpoint_exposes_memory_backend() -> None:
    client = TestClient(app)
    response = client.get("/status")
    assert response.status_code == 200
    payload = response.json()
    assert "memory_backend" in payload
    assert "telegram" in payload
    assert "configured" in payload["telegram"]
    assert "available" in payload["telegram"]
    assert "fs_watch" in payload


def test_metrics_and_admin_endpoints() -> None:
    client = TestClient(app)

    metrics_response = client.get("/metrics")
    admin_response = client.get("/admin")
    admin_css = client.get("/admin/static/panel.css")
    admin_js = client.get("/admin/static/panel.js")
    recent_tasks_response = client.get("/tasks/recent")

    assert metrics_response.status_code == 200
    assert "task_count" in metrics_response.json()
    assert admin_response.status_code == 200
    assert "Чат" in admin_response.text
    assert "Настройки" in admin_response.text
    assert "Диалог с ИИ" in admin_response.text
    assert 'id="chat-dialog-root"' in admin_response.text
    assert 'data-view="overview"' in admin_response.text
    assert "Local AI Agent" in admin_response.text
    assert admin_css.status_code == 200
    assert "Cormorant" in admin_css.text or "--gold" in admin_css.text
    assert "chat-dialog" in admin_css.text
    assert admin_js.status_code == 200
    assert "admin-chat" in admin_js.text
    assert "openChatDialog" in admin_js.text
    assert recent_tasks_response.status_code == 200
    assert isinstance(recent_tasks_response.json(), list)


def test_settings_get_masks_secrets() -> None:
    client = TestClient(app)
    response = client.get("/settings")
    assert response.status_code == 200
    payload = response.json()
    assert "values" in payload
    assert "secrets" in payload
    assert "api_token" not in payload["values"]
    assert "telegram_bot_token" not in payload["values"]
    assert "api_token" in payload["secrets"]
    assert "configured" in payload["secrets"]["api_token"]
    assert payload["applies_after_restart"] is True


def test_settings_put_merges_env_file(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# keep me\nLOCAL_AI_AGENT_APP_NAME=old-name\nLOCAL_AI_AGENT_ENV=dev\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = Settings(
        app_name="old-name",
        env="dev",
        api_token=None,
        require_api_token=False,
    )
    with patch("apps.api.main.load_settings", return_value=settings):
        client = TestClient(create_app())
        response = client.put(
            "/settings",
            json={"updates": {"app_name": "luxury-panel", "log_level": "DEBUG"}},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["saved"] is True
    assert body["restart_required"] is True
    text = env_path.read_text(encoding="utf-8")
    assert "# keep me" in text
    assert "LOCAL_AI_AGENT_APP_NAME=luxury-panel" in text
    assert "LOCAL_AI_AGENT_LOG_LEVEL=DEBUG" in text
    assert "LOCAL_AI_AGENT_ENV=dev" in text


def test_memory_endpoints_return_lists() -> None:
    client = TestClient(app)

    list_response = client.get("/memory")
    search_response = client.get("/memory/search", params={"q": "runtime"})

    assert list_response.status_code == 200
    assert isinstance(list_response.json()["items"], list)
    assert search_response.status_code == 200
    assert isinstance(search_response.json(), list)


def test_memory_endpoint_supports_pagination_and_kind_filtering(tmp_path: Path) -> None:
    client = _client(tmp_path)
    created_ids: list[str] = []

    try:
        for payload in (
            {
                "kind": "preference",
                "key": "memory-page-a",
                "value": "first item",
                "tags": ["page-test"],
            },
            {
                "kind": "rule",
                "key": "memory-page-b",
                "value": "second item",
                "tags": ["page-test"],
            },
            {
                "kind": "preference",
                "key": "memory-page-c",
                "value": "third item",
                "tags": ["page-test"],
            },
        ):
            response = client.post("/memory", json=payload)
            assert response.status_code == 200
            created_ids.append(response.json()["id"])

        filtered = client.get(
            "/memory",
            params={
                "q": "memory-page",
                "kind": "preference",
                "limit": 1,
                "offset": 1,
            },
        )
        assert filtered.status_code == 200

        body = filtered.json()
        assert body["limit"] == 1
        assert body["offset"] == 1
        assert body["query"] == "memory-page"
        assert body["kind"] == "preference"
        assert len(body["items"]) == 1
        assert body["items"][0]["kind"] == "preference"
    finally:
        for memory_id in created_ids:
            client.delete(f"/memory/{memory_id}")


def test_create_and_delete_memory_endpoints(tmp_path: Path) -> None:
    client = _client(tmp_path)

    create_response = client.post(
        "/memory",
        json={
            "kind": "preference",
            "key": "api-test",
            "value": "created through endpoint",
            "tags": ["test"],
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()

    delete_response = client.delete(f"/memory/{created['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True


def test_patch_memory_endpoint(tmp_path: Path) -> None:
    client = _client(tmp_path)

    create_response = client.post(
        "/memory",
        json={
            "kind": "preference",
            "key": "patch-test",
            "value": "before",
            "tags": ["patch"],
        },
    )
    created = create_response.json()

    patch_response = client.patch(
        f"/memory/{created['id']}",
        json={"value": "after", "tags": ["patched"]},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["updated"] is True
    assert patch_response.json()["item"]["value"] == "after"

    client.delete(f"/memory/{created['id']}")


def test_api_approve_and_get_task_endpoints(tmp_path: Path) -> None:
    from packages.core import Action, ActionMode, Task
    from services.orchestrator import OrchestratorRuntime

    settings = _settings(tmp_path)
    with patch("apps.api.main.load_settings", return_value=settings):
        client = TestClient(create_app())

    runtime = OrchestratorRuntime(settings)
    task = Task(
        title="ApproveAPI",
        goal="needs approval",
        actions=[
            Action(
                name="noop",
                description="sensitive",
                mode=ActionMode.EXECUTE,
                side_effects=["delete"],
            )
        ],
    )
    paused = runtime.run_task(task)
    assert paused.success is False

    missing = client.get("/tasks/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 200
    assert missing.json()["found"] is False

    with patch("apps.api.main.load_settings", return_value=settings):
        shared = TestClient(create_app())
    approve = shared.post(
        f"/tasks/{task.id}/approve",
        json={"approved": True, "reviewer": "api"},
    )
    assert approve.status_code == 200
    assert approve.json()["result"]["success"] is True


def test_fs_watch_endpoints(tmp_path: Path) -> None:
    mock_watch = MagicMock()
    mock_watch.start.return_value = True
    mock_watch.is_available.return_value = True
    mock_watch.watch_path = tmp_path
    mock_watch.poll_once.return_value = []
    mock_watch.drain_events.return_value = [
        {"event_type": "created", "src_path": str(tmp_path / "file.txt")}
    ]
    mock_watch.stop.return_value = None

    settings = _settings(tmp_path)
    with (
        patch("apps.api.main.load_settings", return_value=settings),
        patch(
            "services.orchestrator.capabilities.WatchdogAdapter",
            return_value=mock_watch,
        ),
    ):
        client = TestClient(create_app())
    start = client.post("/fs/watch/start", json={"seconds": 0})
    assert start.status_code == 200
    assert start.json()["started"] is True

    events = client.get("/fs/watch/events")
    assert events.status_code == 200
    assert events.json()["events"][0]["event_type"] == "created"

    stop = client.post("/fs/watch/stop")
    assert stop.status_code == 200
    assert stop.json()["stopped"] is True
    mock_watch.stop.assert_called()
