from __future__ import annotations

from pydantic import BaseModel, Field


class SandboxRequest(BaseModel):
    command: list[str]
    language: str
    timeout_seconds: int = Field(default=10, ge=1, le=120)
    allow_network: bool = False
    prefer_docker: bool = False


class SandboxExecution(BaseModel):
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    retries: int = 0
    mode: str = "local"  # docker | local
    degraded: bool = False
    isolated: bool = False
