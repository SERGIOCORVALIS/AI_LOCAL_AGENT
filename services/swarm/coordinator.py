from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import BaseModel, Field

from packages.core import Observation, Task
from packages.routing import RouteDecision, TaskRouter
from services.llm import OLLAMA_UNAVAILABLE, AgentModelConfig, OllamaClient
from services.perception import CodeIntelligence


class SwarmDispatch(BaseModel):
    route: RouteDecision
    role_outputs: list[str] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)


class SwarmCoordinator:
    """Coordinates role fan-out with AST tools and Ollama role reasoning."""

    def __init__(
        self,
        router: TaskRouter | None = None,
        ollama_client: OllamaClient | None = None,
        model: str = "gemma4",
        router_model: str | None = None,
        agents: AgentModelConfig | None = None,
    ) -> None:
        self._router = router or TaskRouter()
        self._code = CodeIntelligence()
        self._ollama = ollama_client
        self._agents = agents or AgentModelConfig(
            primary=model,
            router=router_model or model,
            vision=model,
            embed="nomic-embed-text",
        )

    def dispatch(self, task: Task) -> SwarmDispatch:
        route = self._router.route(task)
        with ThreadPoolExecutor(max_workers=route.parallelism) as executor:
            outputs = list(
                executor.map(
                    lambda role: self._run_role(role, task, route),
                    route.assigned_roles,
                )
            )

        observations = [
            Observation(
                source="swarm",
                summary="Swarm dispatch completed.",
                details={
                    "tier": route.tier,
                    "parallelism": route.parallelism,
                    "roles": route.assigned_roles,
                    "target_model": route.target_model,
                    "role_models": {
                        role: self._model_for_role(role, route)
                        for role in route.assigned_roles
                    },
                    "outputs": outputs,
                },
            )
        ]
        return SwarmDispatch(route=route, role_outputs=outputs, observations=observations)

    def _model_for_role(self, role: str, route: RouteDecision) -> str:
        if role == "router":
            return self._agents.for_role("router")
        if route.target_model not in {"", "tooling-fastpath"}:
            return route.target_model
        return self._agents.for_role(role)

    def _run_role(self, role: str, task: Task, route: RouteDecision) -> str:
        heuristic = self._heuristic_role(role, task)
        if self._ollama is None:
            return heuristic
        model = self._model_for_role(role, route)
        if role == "coder":
            prompt = (
                "You are the coder agent. Given the AST index summary below, "
                "summarize key symbols and risks in one short paragraph.\n"
                f"Task: {task.title}\nGoal: {task.goal}\nAST: {heuristic}"
            )
        else:
            prompt = (
                f"You are the '{role}' agent in a local swarm.\n"
                f"Task title: {task.title}\n"
                f"Goal: {task.goal}\n"
                f"Local analysis: {heuristic}\n"
                "Reply with a concise actionable finding in one short paragraph."
            )
        llm = self._ollama.generate(model, prompt)
        if llm == OLLAMA_UNAVAILABLE:
            return f"{heuristic} [{OLLAMA_UNAVAILABLE}]"
        if role == "coder":
            return f"{heuristic} | llm: {llm}"
        return f"{role}: {llm}"

    def _heuristic_role(self, role: str, task: Task) -> str:
        goal = task.goal.lower()
        if role == "router":
            return (
                f"router: selected path for goal_len={len(task.goal)} "
                f"actions={len(task.actions)}"
            )
        if role == "coder":
            root = Path("packages") if Path("packages").exists() else Path(".")
            summary = self._code.index_python_tree(root)
            return (
                f"coder: indexed files={len(summary.python_files)} "
                f"symbols={sum(len(items) for items in summary.symbols.values())}"
            )
        if role == "researcher":
            keywords = sorted(
                {token for token in goal.replace(",", " ").split() if len(token) > 3}
            )
            web_hits = [
                obs.summary
                for obs in task.observations
                if obs.source == "capability.web_search"
            ]
            search_note = (
                f" web_search={web_hits[0]}"
                if web_hits
                else (
                    " web_search=planned"
                    if any(action.name == "web_search" for action in task.actions)
                    else ""
                )
            )
            return (
                f"researcher: keywords={','.join(keywords[:8]) or 'none'}"
                f"{search_note}"
            )
        if role == "reviewer":
            risks: list[str] = []
            if any(token in goal for token in ("delete", "overwrite", "admin")):
                risks.append("destructive-intent")
            if "http://" in goal or "https://" in goal:
                risks.append("network-io")
            if any(action.name == "coding_agent" for action in task.actions):
                risks.append("external-coding-agent")
            return f"reviewer: risks={','.join(risks) or 'none'}"
        if role == "ops":
            return (
                f"ops: prepare runtime artifacts for task '{task.title}' "
                f"priority={task.priority}"
            )
        return f"{role}: analyzed goal '{task.goal[:80]}'"
