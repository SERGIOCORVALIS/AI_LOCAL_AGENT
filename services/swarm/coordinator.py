from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, Field

from packages.core import Observation, Task
from packages.routing import RouteDecision, TaskRouter


class SwarmDispatch(BaseModel):
    route: RouteDecision
    role_outputs: list[str] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)


class SwarmCoordinator:
    """Coordinates role fan-out for routed tasks."""

    def __init__(self, router: TaskRouter | None = None) -> None:
        self._router = router or TaskRouter()

    def dispatch(self, task: Task) -> SwarmDispatch:
        route = self._router.route(task)
        with ThreadPoolExecutor(max_workers=route.parallelism) as executor:
            outputs = list(executor.map(self._run_role, route.assigned_roles))

        observations = [
            Observation(
                source="swarm",
                summary="Swarm dispatch completed.",
                details={
                    "tier": route.tier,
                    "parallelism": route.parallelism,
                    "roles": route.assigned_roles,
                },
            )
        ]
        return SwarmDispatch(route=route, role_outputs=outputs, observations=observations)

    def _run_role(self, role: str) -> str:
        return f"{role}:ready"
