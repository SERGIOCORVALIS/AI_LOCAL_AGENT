from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from packages.core import Task, TaskPriority


class ComplexityTier(StrEnum):
    TRIVIAL = "trivial"
    STANDARD = "standard"
    COMPLEX = "complex"
    HEAVY = "heavy"


class RouteDecision(BaseModel):
    tier: ComplexityTier
    target_model: str
    use_tools_directly: bool
    parallelism: int = Field(default=1, ge=1)
    assigned_roles: list[str] = Field(default_factory=list)
    reason: str


class TaskRouter:
    """Cost-aware routing for local model and tool execution."""

    def route(self, task: Task) -> RouteDecision:
        complexity = self._score_complexity(task)

        if complexity == ComplexityTier.TRIVIAL:
            return RouteDecision(
                tier=complexity,
                target_model="tooling-fastpath",
                use_tools_directly=True,
                assigned_roles=["ops"],
                reason="Low complexity task can use direct tooling without heavy reasoning.",
            )

        if complexity == ComplexityTier.STANDARD:
            return RouteDecision(
                tier=complexity,
                target_model="gemma-4-2b",
                use_tools_directly=False,
                assigned_roles=["router", "ops"],
                reason="Standard task fits lightweight routing and single-role execution.",
            )

        if complexity == ComplexityTier.COMPLEX:
            return RouteDecision(
                tier=complexity,
                target_model="gemma-4-31b",
                use_tools_directly=False,
                parallelism=2,
                assigned_roles=["router", "coder", "reviewer"],
                reason="Complex task benefits from heavier reasoning and reviewer pass.",
            )

        return RouteDecision(
            tier=complexity,
            target_model="gemma-4-31b",
            use_tools_directly=False,
            parallelism=4,
            assigned_roles=["router", "coder", "researcher", "reviewer", "ops"],
            reason="Heavy task requires swarm execution and maximum local reasoning power.",
        )

    def _score_complexity(self, task: Task) -> ComplexityTier:
        action_count = len(task.actions)
        observation_count = len(task.observations)
        if task.priority == TaskPriority.CRITICAL or action_count >= 5:
            return ComplexityTier.HEAVY
        if task.priority == TaskPriority.HIGH or action_count >= 3:
            return ComplexityTier.COMPLEX
        if observation_count > 0 or action_count >= 1:
            return ComplexityTier.STANDARD
        return ComplexityTier.TRIVIAL
