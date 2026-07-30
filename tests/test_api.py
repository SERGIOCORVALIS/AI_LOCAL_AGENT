from fastapi.testclient import TestClient

from apps.api.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_run_task_endpoint() -> None:
    client = TestClient(app)
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
    assert "memory_backend" in response.json()


def test_metrics_and_admin_endpoints() -> None:
    client = TestClient(app)

    metrics_response = client.get("/metrics")
    admin_response = client.get("/admin")
    recent_tasks_response = client.get("/tasks/recent")

    assert metrics_response.status_code == 200
    assert "task_count" in metrics_response.json()
    assert admin_response.status_code == 200
    assert "Local management panel" in admin_response.text
    assert recent_tasks_response.status_code == 200
    assert isinstance(recent_tasks_response.json(), list)


def test_memory_endpoints_return_lists() -> None:
    client = TestClient(app)

    list_response = client.get("/memory")
    search_response = client.get("/memory/search", params={"q": "runtime"})

    assert list_response.status_code == 200
    assert isinstance(list_response.json()["items"], list)
    assert search_response.status_code == 200
    assert isinstance(search_response.json(), list)


def test_memory_endpoint_supports_pagination_and_kind_filtering() -> None:
    client = TestClient(app)
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


def test_create_and_delete_memory_endpoints() -> None:
    client = TestClient(app)

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


def test_patch_memory_endpoint() -> None:
    client = TestClient(app)

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
