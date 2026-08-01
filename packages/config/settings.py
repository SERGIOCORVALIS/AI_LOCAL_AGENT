from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="local-ai-agent")
    env: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    # Prefer short family ids; runtime resolves to installed Ollama tags.
    model_primary: str = Field(default="gemma4")
    model_router: str = Field(default="gemma4")
    model_vision: str = Field(default="gemma4")
    model_embed: str = Field(default="nomic-embed-text")
    # None = keep native Ollama embedding size; set to force a fixed projection.
    embedding_dimensions: int | None = Field(default=None)
    embedding_prefer_native: bool = Field(default=True)
    ollama_url: str = Field(default="http://127.0.0.1:11434")
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_collection: str = Field(default="agent_memory")
    runtime_log_path: Path = Field(default=Path("./runtime/logs/agent.log"))
    audit_log_path: Path = Field(default=Path("./runtime/audit/events.jsonl"))
    task_store_path: Path = Field(default=Path("./runtime/tasks/state.json"))
    memory_store_path: Path = Field(
        default=Path("./runtime/memory/preferences.json")
    )
    backup_dir: Path = Field(default=Path("./backups"))
    downloads_watch_path: Path = Field(default=Path.home() / "Downloads")
    admin_ui_title: str = Field(default="Local AI Agent Admin")
    sandbox_prefer_docker: bool = Field(default=True)
    # Local Ollama-launched coding CLIs (codex / opencode / droid / claude).
    coding_agents_enabled: bool = Field(default=True)
    coding_agent_default: str = Field(default="auto")
    coding_agent_timeout_seconds: float = Field(default=300.0)
    # Empty = use model_primary at runtime.
    coding_agent_model: str = Field(default="")
    # None/empty = auto-detect language (needed for Russian voice).
    stt_language: str | None = Field(default=None)
    api_bind_host: str = Field(default="127.0.0.1")
    api_token: str | None = None
    require_api_token: bool = Field(default=False)
    trusted_hosts_raw: str = Field(default="127.0.0.1,localhost")
    allowed_execute_actions_raw: str = Field(
        default=(
            "bootstrap,noop,reflect,sandbox_run,web_fetch,web_search,write_file,"
            "coding_agent,code_intel,fs_scan,fs_watch,vision_inspect,browser_open"
        )
    )
    denied_execute_actions_raw: str = Field(
        default="format_disk,wipe_system,exfiltrate_secrets"
    )
    telegram_bot_token: str | None = None
    telegram_admin_chat_id: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="LOCAL_AI_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("embedding_dimensions", mode="before")
    @classmethod
    def _empty_embedding_dimensions(cls, value: object) -> object:
        if value == "" or value is None:
            return None
        return value

    @field_validator("api_token", "telegram_bot_token", mode="before")
    @classmethod
    def _clean_secret_fields(cls, value: object) -> object:
        if value == "" or value is None:
            return None
        if isinstance(value, str):
            # Strip inline .env comments: TOKEN=secret # note
            cleaned = value.split("#", 1)[0].strip().strip("\"'")
            # Treat placeholder templates as unset.
            if cleaned.startswith("(") and cleaned.endswith(")"):
                return None
            if "YOUR_" in cleaned.upper():
                return None
            return cleaned or None
        return value

    @field_validator("telegram_admin_chat_id", mode="before")
    @classmethod
    def _clean_telegram_chat_id(cls, value: object) -> object:
        if value == "" or value is None:
            return None
        if isinstance(value, str):
            cleaned = value.split("#", 1)[0].strip().strip("\"'")
            if cleaned.startswith("(") and cleaned.endswith(")"):
                return None
            if "YOUR_" in cleaned.upper():
                return None
            return cleaned or None
        return value

    @field_validator("stt_language", mode="before")
    @classmethod
    def _empty_stt_language(cls, value: object) -> object:
        if value == "" or value is None:
            return None
        if isinstance(value, str) and value.strip().lower() in {"auto", "none", "detect"}:
            return None
        return value

    def validate_production_guards(self) -> None:
        """Fail fast for unsafe prod configuration."""
        if self.env.lower() != "prod":
            return
        if self.require_api_token and not self.api_token:
            raise ValueError(
                "LOCAL_AI_AGENT_ENV=prod with REQUIRE_API_TOKEN=true requires "
                "LOCAL_AI_AGENT_API_TOKEN to be set."
            )

    @property
    def trusted_hosts(self) -> list[str]:
        return sorted(self._split_csv(self.trusted_hosts_raw))

    @property
    def allowed_execute_actions(self) -> set[str]:
        return self._split_csv(self.allowed_execute_actions_raw)

    @property
    def denied_execute_actions(self) -> set[str]:
        return self._split_csv(self.denied_execute_actions_raw)

    @property
    def is_prod(self) -> bool:
        return self.env.lower() == "prod"

    @property
    def api_token_required(self) -> bool:
        """True when mutating API routes must present the configured token."""
        return bool(self.api_token) or self.require_api_token

    @staticmethod
    def _split_csv(raw_value: str) -> set[str]:
        return {
            item.strip().lower()
            for item in str(raw_value).split(",")
            if item.strip()
        }


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    settings = Settings()
    settings.validate_production_guards()
    return settings
