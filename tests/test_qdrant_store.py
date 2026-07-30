import httpx

from packages.memory import MemoryItem, MemoryKind
from services.memory import QdrantMemoryStore


def test_qdrant_store_ping_upsert_and_search() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/collections":
            return httpx.Response(200, json={"result": {"collections": []}})
        if request.method == "PUT" and request.url.path == "/collections/agent_memory":
            return httpx.Response(200, json={"result": True})
        if request.method == "PUT" and request.url.path == "/collections/agent_memory/points":
            return httpx.Response(200, json={"result": {"status": "acknowledged"}})
        if (
            request.method == "POST"
            and request.url.path == "/collections/agent_memory/points/search"
        ):
            body = request.read().decode("utf-8")
            assert '"limit":5' in body
            assert '"value":"preference"' in body
            return httpx.Response(
                200,
                json={
                    "result": [
                        {
                            "payload": MemoryItem(
                                kind=MemoryKind.PREFERENCE,
                                key="style",
                                value="strict typing",
                                tags=["python"],
                            ).model_dump(mode="json")
                        }
                    ]
                },
            )
        if request.method == "POST" and request.url.path == "/collections/agent_memory/points":
            return httpx.Response(
                200,
                json={
                    "result": [
                        {
                            "payload": MemoryItem(
                                id=item.id,
                                kind=MemoryKind.PREFERENCE,
                                key="style",
                                value="strict typing",
                                tags=["python"],
                            ).model_dump(mode="json")
                        }
                    ]
                },
            )
        if (
            request.method == "POST"
            and request.url.path == "/collections/agent_memory/points/delete"
        ):
            return httpx.Response(200, json={"result": {"status": "acknowledged"}})
        return httpx.Response(404, json={"status": "missing"})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://qdrant")
    store = QdrantMemoryStore(
        url="http://qdrant",
        collection="agent_memory",
        client=client,
    )
    item = MemoryItem(
        kind=MemoryKind.PREFERENCE,
        key="style",
        value="strict typing",
        tags=["python"],
    )

    assert store.ping() is True
    upsert_result = store.upsert(item)
    remembered = store.remember(MemoryKind.RULE, "safety", "dry-run first", ["policy"])
    search_result = store.search("strict", limit=5, kind=MemoryKind.PREFERENCE)

    assert upsert_result["operation_acknowledged"] is True
    assert remembered.key == "safety"
    assert search_result[0].value == "strict typing"
    updated = store.update(str(item.id), value="updated typing")
    assert updated is not None
    assert updated.value == "updated typing"
    assert store.delete(str(item.id)) is True


def test_qdrant_store_ignores_existing_collection_conflict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PUT" and request.url.path == "/collections/agent_memory":
            return httpx.Response(409, json={"status": "exists"})
        if (
            request.method == "POST"
            and request.url.path == "/collections/agent_memory/points/search"
        ):
            return httpx.Response(200, json={"result": []})
        return httpx.Response(200, json={"result": {}})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://qdrant")
    store = QdrantMemoryStore("http://qdrant", "agent_memory", client=client)

    assert store.search("anything") == []


def test_qdrant_store_retrieve_scroll_supports_offset_and_kind_filter() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PUT" and request.url.path == "/collections/agent_memory":
            return httpx.Response(200, json={"result": True})
        if (
            request.method == "POST"
            and request.url.path == "/collections/agent_memory/points/scroll"
        ):
            body = request.read().decode("utf-8")
            assert '"limit":3' in body
            assert '"value":"preference"' in body
            return httpx.Response(
                200,
                json={
                    "result": {
                        "points": [
                            {
                                "payload": MemoryItem(
                                    kind=MemoryKind.PREFERENCE,
                                    key="a",
                                    value="first",
                                    tags=["page"],
                                ).model_dump(mode="json")
                            },
                            {
                                "payload": MemoryItem(
                                    kind=MemoryKind.PREFERENCE,
                                    key="b",
                                    value="second",
                                    tags=["page"],
                                ).model_dump(mode="json")
                            },
                            {
                                "payload": MemoryItem(
                                    kind=MemoryKind.PREFERENCE,
                                    key="c",
                                    value="third",
                                    tags=["page"],
                                ).model_dump(mode="json")
                            },
                        ]
                    }
                },
            )
        return httpx.Response(404, json={"status": "missing"})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://qdrant")
    store = QdrantMemoryStore("http://qdrant", "agent_memory", client=client)

    result = store.retrieve("", limit=2, offset=1, kind=MemoryKind.PREFERENCE)

    assert len(result) == 2
    assert result[0].key == "b"
    assert result[1].key == "c"
