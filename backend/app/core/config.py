from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FactoryOps AI Copilot"
    environment: str = "local"
    llm_provider: str = Field(default="mock", validation_alias="LLM_PROVIDER")
    openrouter_api_key: str | None = Field(default=None, validation_alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(
        default="openai/gpt-4o-mini", validation_alias="OPENROUTER_MODEL"
    )
    database_path: str = Field(default="data/factoryops.sqlite3", validation_alias="DATABASE_PATH")
    runs_jsonl_path: str = Field(default="data/runs.jsonl", validation_alias="RUNS_JSONL_PATH")
    uploads_dir: str = Field(default="data/uploads", validation_alias="UPLOADS_DIR")
    cors_origins: str = Field(default="http://localhost:5173", validation_alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def masked_provider_config(self) -> dict[str, str | bool]:
        openrouter_configured = bool(
            self.openrouter_api_key and not self.openrouter_api_key.startswith("your_")
        )
        return {
            "provider": self.llm_provider,
            "openrouter_configured": openrouter_configured,
            "openrouter_model": self.openrouter_model,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
