from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.core.models import utc_now


class MemoryKind(StrEnum):
    PREFERENCE = "preference"
    RULE = "rule"
    HABIT = "habit"
    FACT = "fact"
    EPISODE = "episode"


class MemoryItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    kind: MemoryKind
    key: str
    value: str
    tags: list[str] = Field(default_factory=list)
    relevance: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
