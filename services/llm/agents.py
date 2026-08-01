from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from services.llm.models import model_is_available, resolve_model_name
from services.llm.ollama_client import OllamaClient

SWARM_ROLES: tuple[str, ...] = ("router", "coder", "researcher", "reviewer", "ops")


class AgentSlot(StrEnum):
    PRIMARY = "primary"
    ROUTER = "router"
    VISION = "vision"
    EMBED = "embed"


ROLE_TO_SLOT: dict[str, AgentSlot] = {
    "router": AgentSlot.ROUTER,
    "coder": AgentSlot.PRIMARY,
    "researcher": AgentSlot.PRIMARY,
    "reviewer": AgentSlot.PRIMARY,
    "ops": AgentSlot.ROUTER,
}


class AgentModelConfig(BaseModel):
    """Configured Ollama models for each agent capability slot."""

    primary: str = "gemma4"
    router: str = "gemma4"
    vision: str = "gemma4"
    embed: str = "nomic-embed-text"

    def slot_model(self, slot: AgentSlot | str) -> str:
        key = AgentSlot(slot)
        return getattr(self, key.value)

    def for_role(self, role: str) -> str:
        slot = ROLE_TO_SLOT.get(role, AgentSlot.PRIMARY)
        return self.slot_model(slot)

    def for_route_target(self, target_model: str) -> str:
        if target_model in {"", "tooling-fastpath"}:
            return self.router
        return target_model

    def as_dict(self) -> dict[str, str]:
        return {
            AgentSlot.PRIMARY.value: self.primary,
            AgentSlot.ROUTER.value: self.router,
            AgentSlot.VISION.value: self.vision,
            AgentSlot.EMBED.value: self.embed,
        }

    def resolve_against(self, installed: list[str]) -> AgentModelConfig:
        """Return a copy with configured ids resolved to installed tags when possible."""
        resolved: dict[str, str] = {}
        for slot, configured in self.as_dict().items():
            match = resolve_model_name(configured, installed)
            resolved[slot] = match or configured
        return AgentModelConfig(**resolved)


def slot_readiness(
    configured: str,
    installed: list[str],
    *,
    online: bool,
) -> dict[str, Any]:
    resolved = resolve_model_name(configured, installed) if online else None
    available = bool(online and resolved)
    hint = None
    if not online:
        hint = "Ollama is offline; start the daemon and retry."
    elif not available:
        hint = f"Model '{configured}' not found. Run: ollama pull {configured}"
    return {
        "configured": configured,
        "resolved": resolved,
        "available": available,
        "hint": hint,
    }


def ollama_agents_readiness(
    ollama_client: OllamaClient | None,
    agents: AgentModelConfig,
) -> dict[str, Any]:
    """Readiness snapshot for Ollama chat/vision/embed slots and swarm roles."""
    if ollama_client is None:
        return {
            "online": False,
            "installed": [],
            "slots": {
                slot: slot_readiness(model, [], online=False)
                for slot, model in agents.as_dict().items()
            },
            "roles": {
                role: {
                    "slot": ROLE_TO_SLOT[role].value,
                    **slot_readiness(agents.for_role(role), [], online=False),
                }
                for role in SWARM_ROLES
            },
            "all_required_available": False,
            "hint": "Ollama client not configured.",
        }

    online = ollama_client.ping()
    installed = ollama_client.list_models() if online else []
    slots = {
        slot: slot_readiness(model, installed, online=online)
        for slot, model in agents.as_dict().items()
    }
    roles = {
        role: {
            "slot": ROLE_TO_SLOT[role].value,
            **slot_readiness(agents.for_role(role), installed, online=online),
        }
        for role in SWARM_ROLES
    }
    required = ("primary", "router", "embed")
    all_ok = online and all(slots[name]["available"] for name in required)
    missing = [
        f"{name}={slots[name]['configured']}"
        for name in required
        if not slots[name]["available"]
    ]
    hint = None
    if not online:
        hint = "Ollama is offline; start it before running agent tasks."
    elif missing:
        hint = "Missing required models: " + ", ".join(missing)
    return {
        "online": online,
        "installed": installed,
        "slots": slots,
        "roles": roles,
        "all_required_available": all_ok,
        "hint": hint,
    }


def agents_from_settings(
    *,
    primary: str,
    router: str,
    vision: str,
    embed: str,
) -> AgentModelConfig:
    return AgentModelConfig(
        primary=primary,
        router=router,
        vision=vision,
        embed=embed,
    )


class ResolvedAgents(BaseModel):
    """Runtime-resolved agent models plus original configuration."""

    configured: AgentModelConfig
    resolved: AgentModelConfig
    installed: list[str] = Field(default_factory=list)
    online: bool = False

    def model_for_role(self, role: str) -> str:
        return self.resolved.for_role(role)

    def model_for_slot(self, slot: AgentSlot | str) -> str:
        return self.resolved.slot_model(slot)


def resolve_agents(
    ollama_client: OllamaClient | None,
    configured: AgentModelConfig,
) -> ResolvedAgents:
    if ollama_client is None or not ollama_client.ping():
        return ResolvedAgents(
            configured=configured,
            resolved=configured,
            installed=[],
            online=False,
        )
    installed = ollama_client.list_models()
    return ResolvedAgents(
        configured=configured,
        resolved=configured.resolve_against(installed),
        installed=installed,
        online=True,
    )


def model_available_for(
    ollama_client: OllamaClient | None,
    model: str,
) -> bool:
    if ollama_client is None or not model:
        return False
    if not ollama_client.ping():
        return False
    return model_is_available(model, ollama_client.list_models())
