from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from packages.core import Task, TaskPriority
from services.llm import OllamaClient


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
    estimated_tokens: int = Field(default=0, ge=0)


class TaskRouter:
    """Cost-aware routing with optional Ollama confirmation."""

    def __init__(
        self,
        primary_model: str = "gemma4",
        router_model: str = "gemma4",
        ollama_client: OllamaClient | None = None,
    ) -> None:
        self._primary_model = primary_model
        self._router_model = router_model
        self._ollama = ollama_client

    def route(self, task: Task) -> RouteDecision:
        baseline = self._heuristic_route(task)
        if self._ollama is None:
            return baseline

        prompt = (
            "Confirm or adjust task routing. Return JSON with keys: "
            "tier, assigned_roles, reason.\n"
            f"goal={task.goal}\n"
            f"actions={[action.name for action in task.actions]}\n"
            f"priority={task.priority}\n"
            f"baseline_tier={baseline.tier}\n"
            f"baseline_roles={baseline.assigned_roles}\n"
            "tier must be one of trivial|standard|complex|heavy."
        )
        payload = self._ollama.chat_json(self._router_model, prompt)
        if payload is None:
            return baseline.model_copy(
                update={"reason": f"{baseline.reason} (ollama_unavailable fallback)"}
            )

        tier_raw = str(payload.get("tier", baseline.tier.value)).lower()
        try:
            tier = ComplexityTier(tier_raw)
        except ValueError:
            tier = baseline.tier

        roles_raw = payload.get("assigned_roles", baseline.assigned_roles)
        roles = (
            [str(item) for item in roles_raw]
            if isinstance(roles_raw, list) and roles_raw
            else baseline.assigned_roles
        )
        reason = str(payload.get("reason", baseline.reason))
        parallelism = {
            ComplexityTier.TRIVIAL: 1,
            ComplexityTier.STANDARD: 1,
            ComplexityTier.COMPLEX: 2,
            ComplexityTier.HEAVY: 4,
        }[tier]
        target = (
            "tooling-fastpath"
            if tier == ComplexityTier.TRIVIAL
            else self._router_model
            if tier == ComplexityTier.STANDARD
            else self._primary_model
        )
        return RouteDecision(
            tier=tier,
            target_model=target,
            use_tools_directly=baseline.use_tools_directly or tier == ComplexityTier.TRIVIAL,
            parallelism=parallelism,
            assigned_roles=roles,
            reason=reason,
            estimated_tokens=baseline.estimated_tokens,
        )

    def _heuristic_route(self, task: Task) -> RouteDecision:
        complexity = self._score_complexity(task)
        goal = task.goal.lower()
        tool_hint = any(
            token in goal
            for token in (
                "http://",
                "https://",
                "sandbox",
                "file",
                "download",
                "browser",
                "search",
                "coding_agent",
            )
        )
        coding_hint = self._is_coding_task(task)
        if coding_hint and complexity in {ComplexityTier.TRIVIAL, ComplexityTier.STANDARD}:
            complexity = ComplexityTier.COMPLEX

        if complexity == ComplexityTier.TRIVIAL:
            return RouteDecision(
                tier=complexity,
                target_model="tooling-fastpath",
                use_tools_directly=True,
                assigned_roles=["ops"],
                reason="Low complexity task can use direct tooling without heavy reasoning.",
                estimated_tokens=256,
            )

        if complexity == ComplexityTier.STANDARD:
            return RouteDecision(
                tier=complexity,
                target_model=self._router_model,
                use_tools_directly=tool_hint,
                assigned_roles=["router", "ops"],
                reason="Standard task fits lightweight routing and single-role execution.",
                estimated_tokens=1024,
            )

        if complexity == ComplexityTier.COMPLEX:
            roles = ["router", "coder", "reviewer"]
            return RouteDecision(
                tier=complexity,
                target_model=self._primary_model,
                use_tools_directly=coding_hint or tool_hint,
                parallelism=2,
                assigned_roles=roles,
                reason=(
                    "Coding task routed with coder role and local coding-agent capability."
                    if coding_hint
                    else "Complex task benefits from heavier reasoning and reviewer pass."
                ),
                estimated_tokens=4096,
            )

        return RouteDecision(
            tier=complexity,
            target_model=self._primary_model,
            use_tools_directly=False,
            parallelism=4,
            assigned_roles=["router", "coder", "researcher", "reviewer", "ops"],
            reason="Heavy task requires swarm execution and maximum local reasoning power.",
            estimated_tokens=8192,
        )

    @staticmethod
    def _is_coding_task(task: Task) -> bool:
        if any(action.name == "coding_agent" for action in task.actions):
            return True
        text = f"{task.title} {task.goal}".lower()
        markers = (
            "implement",
            "refactor",
            "fix",
            "patch",
            "write tests",
            "код",
            "review code",
            "codex",
            "opencode",
            "droid",
            "claude",
        )
        return any(token in text for token in markers)

    def _score_complexity(self, task: Task) -> ComplexityTier:
        action_count = len(task.actions)
        observation_count = len(task.observations)
        goal_len = len(task.goal)
        if task.priority == TaskPriority.CRITICAL or action_count >= 5 or goal_len > 400:
            return ComplexityTier.HEAVY
        if task.priority == TaskPriority.HIGH or action_count >= 3 or goal_len > 180:
            return ComplexityTier.COMPLEX
        if observation_count > 0 or action_count >= 1 or goal_len > 40:
            return ComplexityTier.STANDARD
        return ComplexityTier.TRIVIAL
