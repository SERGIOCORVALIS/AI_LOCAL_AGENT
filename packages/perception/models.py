from __future__ import annotations

from pydantic import BaseModel, Field


class WebDocument(BaseModel):
    url: str
    title: str
    markdown: str
    links: list[str] = Field(default_factory=list)


class WebSearchResult(BaseModel):
    title: str
    url: str
    snippet: str = ""


class WebSearchResponse(BaseModel):
    query: str
    provider: str = "duckduckgo"
    results: list[WebSearchResult] = Field(default_factory=list)


class ScreenshotAnalysis(BaseModel):
    path: str
    width: int
    height: int
    summary: str
    labels: list[str] = Field(default_factory=list)


class CodeGraphSummary(BaseModel):
    root: str
    python_files: list[str] = Field(default_factory=list)
    import_edges: dict[str, list[str]] = Field(default_factory=dict)
    symbols: dict[str, list[str]] = Field(default_factory=dict)
    call_edges: dict[str, list[str]] = Field(default_factory=dict)
