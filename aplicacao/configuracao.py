from functools import lru_cache
from pathlib import Path
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Centralizes environment configuration loaded from .env and defaults."""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    gemini_fallback_models: str = "gemini-3.5-flash,gemini-3.8-flash,gemini-3.5-flash-lite"

    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_env: str = "development"

    n8n_webhook_url: str = Field(
        default="http://localhost:5678/webhook/resumir-texto",
        validation_alias=AliasChoices("AUTOMATION_WEBHOOK_URL", "N8N_WEBHOOK_URL"),
    )

    base_dir: Path = Path(__file__).resolve().parent.parent
    history_file_path: Path = Path("dados/historico_resumos.json")
    max_history_items: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resolved_history_path(self) -> Path:
        if self.history_file_path.is_absolute():
            return self.history_file_path
        return self.base_dir / self.history_file_path

    @property
    def fallback_model_list(self) -> list[str]:
        return [
            item.strip()
            for item in self.gemini_fallback_models.split(",")
            if item.strip()
        ]

    @property
    def frontend_dir(self) -> Path:
        return self.base_dir / "interface"


@lru_cache
def get_settings() -> AppSettings:
    """Returns a cached settings instance so .env is parsed once per process."""
    return AppSettings()
