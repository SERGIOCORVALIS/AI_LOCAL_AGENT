from __future__ import annotations

from pydantic import BaseModel, Field


class WebDocument(BaseModel):
    url: str
    title: str
    markdown: str


class ScreenshotAnalysis(BaseModel):
    path: str
    width: int
    height: int
    summary: str


class CodeGraphSummary(BaseModel):
    root: str
    python_files: list[str] = Field(default_factory=list)
    import_edges: dict[str, list[str]] = Field(default_factory=dict)
