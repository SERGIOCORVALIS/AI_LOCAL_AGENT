from __future__ import annotations

from pydantic import BaseModel, Field


class FileRecord(BaseModel):
    path: str
    suffix: str
    sha256: str
    size_bytes: int
    category: str


class FileRouteProposal(BaseModel):
    source_path: str
    suggested_name: str
    target_bucket: str
    dry_run_only: bool = True
    reasons: list[str] = Field(default_factory=list)
