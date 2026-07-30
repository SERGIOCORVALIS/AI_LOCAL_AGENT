from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="local-ai-agent")
    env: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    model_primary: str = Field(default="gemma-4-31b")
    model_router: str = Field(default="gemma-4-2b")
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
    allowed_execute_actions_raw: str = Field(
        default="bootstrap,noop"
    )
    telegram_bot_token: str | None = None
    telegram_admin_chat_id: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="LOCAL_AI_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_execute_actions(self) -> set[str]:
        raw_value = str(self.allowed_execute_actions_raw)
        return {
            item.strip().lower()
            for item in raw_value.split(",")
            if item.strip()
        }


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    return Settings()
