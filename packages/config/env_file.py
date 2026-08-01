"""Read/merge/write LOCAL_AI_AGENT_* keys in a .env file."""

from __future__ import annotations

from pathlib import Path

ENV_PREFIX = "LOCAL_AI_AGENT_"

# Settings field name -> env key (without relying on pydantic internals).
SETTINGS_ENV_KEYS: dict[str, str] = {
    "app_name": "LOCAL_AI_AGENT_APP_NAME",
    "env": "LOCAL_AI_AGENT_ENV",
    "log_level": "LOCAL_AI_AGENT_LOG_LEVEL",
    "model_primary": "LOCAL_AI_AGENT_MODEL_PRIMARY",
    "model_router": "LOCAL_AI_AGENT_MODEL_ROUTER",
    "model_vision": "LOCAL_AI_AGENT_MODEL_VISION",
    "model_embed": "LOCAL_AI_AGENT_MODEL_EMBED",
    "embedding_dimensions": "LOCAL_AI_AGENT_EMBEDDING_DIMENSIONS",
    "embedding_prefer_native": "LOCAL_AI_AGENT_EMBEDDING_PREFER_NATIVE",
    "ollama_url": "LOCAL_AI_AGENT_OLLAMA_URL",
    "qdrant_url": "LOCAL_AI_AGENT_QDRANT_URL",
    "qdrant_collection": "LOCAL_AI_AGENT_QDRANT_COLLECTION",
    "runtime_log_path": "LOCAL_AI_AGENT_RUNTIME_LOG_PATH",
    "audit_log_path": "LOCAL_AI_AGENT_AUDIT_LOG_PATH",
    "task_store_path": "LOCAL_AI_AGENT_TASK_STORE_PATH",
    "memory_store_path": "LOCAL_AI_AGENT_MEMORY_STORE_PATH",
    "backup_dir": "LOCAL_AI_AGENT_BACKUP_DIR",
    "downloads_watch_path": "LOCAL_AI_AGENT_DOWNLOADS_WATCH_PATH",
    "admin_ui_title": "LOCAL_AI_AGENT_ADMIN_UI_TITLE",
    "sandbox_prefer_docker": "LOCAL_AI_AGENT_SANDBOX_PREFER_DOCKER",
    "coding_agents_enabled": "LOCAL_AI_AGENT_CODING_AGENTS_ENABLED",
    "coding_agent_default": "LOCAL_AI_AGENT_CODING_AGENT_DEFAULT",
    "coding_agent_timeout_seconds": "LOCAL_AI_AGENT_CODING_AGENT_TIMEOUT_SECONDS",
    "coding_agent_model": "LOCAL_AI_AGENT_CODING_AGENT_MODEL",
    "coding_agents_url": "LOCAL_AI_AGENT_CODING_AGENTS_URL",
    "stt_language": "LOCAL_AI_AGENT_STT_LANGUAGE",
    "api_bind_host": "LOCAL_AI_AGENT_API_BIND_HOST",
    "api_token": "LOCAL_AI_AGENT_API_TOKEN",
    "require_api_token": "LOCAL_AI_AGENT_REQUIRE_API_TOKEN",
    "trusted_hosts_raw": "LOCAL_AI_AGENT_TRUSTED_HOSTS",
    "allowed_execute_actions_raw": "LOCAL_AI_AGENT_ALLOWED_EXECUTE_ACTIONS_RAW",
    "denied_execute_actions_raw": "LOCAL_AI_AGENT_DENIED_EXECUTE_ACTIONS_RAW",
    "telegram_bot_token": "LOCAL_AI_AGENT_TELEGRAM_BOT_TOKEN",
    "telegram_admin_chat_id": "LOCAL_AI_AGENT_TELEGRAM_ADMIN_CHAT_ID",
}

SECRET_FIELDS = frozenset({"api_token", "telegram_bot_token"})
WRITABLE_FIELDS = frozenset(SETTINGS_ENV_KEYS)


def default_env_path() -> Path:
    return Path.cwd() / ".env"


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE pairs; skip blanks and comments."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip()
    return values


def upsert_env_values(path: Path, updates: dict[str, str]) -> Path:
    """Merge updates into .env, preserving comments and unrelated keys.

    Only keys starting with LOCAL_AI_AGENT_ are accepted.
    Empty-string values clear the key (write KEY=).
    """
    sanitized: dict[str, str] = {}
    for key, value in updates.items():
        if not key.startswith(ENV_PREFIX):
            raise ValueError(f"Refusing to write non-agent env key: {key}")
        sanitized[key] = "" if value is None else str(value)

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            out.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in sanitized:
            out.append(f"{key}={sanitized[key]}")
            seen.add(key)
        else:
            out.append(line)

    for key, value in sanitized.items():
        if key not in seen:
            out.append(f"{key}={value}")

    text = "\n".join(out)
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
    return path


def field_to_env_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Path):
        return str(value)
    return str(value)
