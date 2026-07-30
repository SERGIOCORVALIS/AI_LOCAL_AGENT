from __future__ import annotations

import httpx

from packages.memory import MemoryItem, MemoryKind


class QdrantMemoryStore:
    """HTTP-backed Qdrant adapter for memory persistence and retrieval."""

    def __init__(
        self,
        url: str,
        collection: str,
        client: httpx.Client | None = None,
    ) -> None:
        self._url = url.rstrip("/")
        self._collection = collection
        self._client = client or httpx.Client(timeout=5.0)

    @property
    def collection(self) -> str:
        return self._collection

    def ping(self) -> bool:
        try:
            response = self._client.get(f"{self._url}/collections")
        except httpx.HTTPError:
            return False
        return response.is_success

    def initialize(self) -> None:
        self._ensure_collection()

    def remember(
        self,
        kind: MemoryKind,
        key: str,
        value: str,
        tags: list[str] | None = None,
    ) -> MemoryItem:
        item = MemoryItem(kind=kind, key=key, value=value, tags=tags or [])
        self.upsert(item)
        return item

    def upsert(self, item: MemoryItem) -> dict[str, str | bool]:
        self._ensure_collection()
        payload = {
            "points": [
                {
                    "id": str(item.id),
                    "vector": self._vectorize(item),
                    "payload": item.model_dump(mode="json"),
                }
            ]
        }
        response = self._client.put(
            f"{self._url}/collections/{self._collection}/points",
            json=payload,
        )
        response.raise_for_status()
        result = response.json().get("result", {})
        return {
            "status": str(result.get("status", "acknowledged")),
            "collection": self._collection,
            "memory_id": str(item.id),
            "operation_acknowledged": bool(response.is_success),
        }

    def search(
        self,
        query: str,
        limit: int = 5,
        offset: int = 0,
        kind: MemoryKind | None = None,
    ) -> list[MemoryItem]:
        self._ensure_collection()
        payload: dict[str, object] = {
            "vector": self._vectorize_text(query),
            "limit": limit + offset,
            "with_payload": True,
        }
        if kind is not None:
            payload["filter"] = self._kind_filter(kind)
        response = self._client.post(
            f"{self._url}/collections/{self._collection}/points/search",
            json=payload,
        )
        response.raise_for_status()
        points = response.json().get("result", [])
        items = [MemoryItem.model_validate(point["payload"]) for point in points]
        return items[offset : offset + limit]

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        offset: int = 0,
        kind: MemoryKind | None = None,
    ) -> list[MemoryItem]:
        if query:
            return self.search(query, limit=limit, offset=offset, kind=kind)

        self._ensure_collection()
        payload: dict[str, object] = {
            "limit": limit + offset,
            "with_payload": True,
            "with_vector": False,
        }
        if kind is not None:
            payload["filter"] = self._kind_filter(kind)
        response = self._client.post(
            f"{self._url}/collections/{self._collection}/points/scroll",
            json=payload,
        )
        response.raise_for_status()
        points = response.json().get("result", {}).get("points", [])
        items = [MemoryItem.model_validate(point["payload"]) for point in points]
        return items[offset : offset + limit]

    def delete(self, memory_id: str) -> bool:
        self._ensure_collection()
        response = self._client.post(
            f"{self._url}/collections/{self._collection}/points/delete",
            json={"points": [memory_id]},
        )
        response.raise_for_status()
        return response.is_success

    def update(
        self,
        memory_id: str,
        *,
        kind: MemoryKind | None = None,
        key: str | None = None,
        value: str | None = None,
        tags: list[str] | None = None,
    ) -> MemoryItem | None:
        self._ensure_collection()
        response = self._client.post(
            f"{self._url}/collections/{self._collection}/points",
            json={"ids": [memory_id], "with_payload": True},
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if not result:
            return None
        target = MemoryItem.model_validate(result[0]["payload"])

        updated_item = target.model_copy(
            update={
                "kind": kind or target.kind,
                "key": key or target.key,
                "value": value or target.value,
                "tags": tags if tags is not None else target.tags,
            }
        )
        self.upsert(updated_item)
        return updated_item

    def _ensure_collection(self) -> None:
        payload = {
            "vectors": {
                "size": 4,
                "distance": "Cosine",
            }
        }
        response = self._client.put(
            f"{self._url}/collections/{self._collection}",
            json=payload,
        )
        if response.status_code == 409:
            return
        response.raise_for_status()

    def _vectorize(self, item: MemoryItem) -> list[float]:
        return self._vectorize_text(f"{item.kind}:{item.key}:{item.value}")

    def _vectorize_text(self, text: str) -> list[float]:
        raw = text.encode("utf-8")[:4]
        padded = raw + b"\x00" * (4 - len(raw))
        return [float(byte) / 255.0 for byte in padded]

    def _kind_filter(self, kind: MemoryKind) -> dict[str, object]:
        return {
            "must": [
                {
                    "key": "kind",
                    "match": {
                        "value": kind,
                    },
                }
            ]
        }
