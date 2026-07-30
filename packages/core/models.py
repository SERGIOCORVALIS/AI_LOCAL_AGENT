from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class TaskState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ActionMode(StrEnum):
    OBSERVE = "observe"
    SUGGEST = "suggest"
    DRY_RUN = "dry-run"
    EXECUTE = "execute"


class PolicyVerdict(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require-approval"
    DENY = "deny"


class ArtifactKind(StrEnum):
    LOG = "log"
    FILE = "file"
    REPORT = "report"
    SCREENSHOT = "screenshot"
    JSON = "json"


class Artifact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    kind: ArtifactKind
    name: str
    uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class Observation(BaseModel):
    source: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class PolicyDecision(BaseModel):
    verdict: PolicyVerdict
    reason: str
    required_approval: bool = False
    tags: list[str] = Field(default_factory=list)


class Action(BaseModel):
    name: str
    description: str
    mode: ActionMode = ActionMode.OBSERVE
    payload: dict[str, Any] = Field(default_factory=dict)
    side_effects: list[str] = Field(default_factory=list)


class ActionResult(BaseModel):
    action: Action
    success: bool
    message: str
    artifacts: list[Artifact] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    policy_decision: PolicyDecision | None = None


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    goal: str
    priority: TaskPriority = TaskPriority.NORMAL
    state: TaskState = TaskState.PENDING
    correlation_id: UUID = Field(default_factory=uuid4)
    actions: list[Action] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def mark_running(self) -> None:
        self.state = TaskState.RUNNING
        self.updated_at = utc_now()

    def mark_succeeded(self) -> None:
        self.state = TaskState.SUCCEEDED
        self.updated_at = utc_now()

    def mark_failed(self, observation: Observation) -> None:
        self.state = TaskState.FAILED
        self.observations.append(observation)
        self.updated_at = utc_now()
