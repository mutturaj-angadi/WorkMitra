import os
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    app_secret_key: str = ""
    database_url: str = "sqlite:///./workplace_compliance.db"
    redis_url: str = ""
    chroma_url: str = ""
    google_api_key: str = ""
    google_model: str = ""
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_project: str = "workplace-compliance-desk"
    embedding_model: str = ""
    prompt_version: str = "v1"
    llm_provider: str = ""
    stub_delay_seconds: float = 1.2
    corpus_dir: str = "corpus"
    api_rate_limit: str = "60/minute"
    otel_exporter_otlp_endpoint: str = ""

    @model_validator(mode="after")
    def apply_optional_defaults(self):
        # Empty values in .env.example are intentional placeholders. Treat them
        # as unset so local development retains its SQLite and no-service defaults.
        if not self.database_url:
            self.database_url = "sqlite:///./workplace_compliance.db"
        if self.llm_provider not in {"gemini", "mock", "stub"}:
            raise ValueError(
                "Set LLM_PROVIDER explicitly to one of: gemini, mock, or stub."
            )
        self.validate_provider()
        return self

    def validate_provider(self) -> None:
        if self.llm_provider == "gemini" and not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")
        if self.llm_provider == "gemini" and not self.google_model:
            raise ValueError(
                "GOOGLE_MODEL must be set at runtime when LLM_PROVIDER=gemini"
            )
        if self.langchain_tracing_v2 and not self.langchain_api_key:
            raise ValueError(
                "LANGCHAIN_API_KEY is required when LangSmith tracing is enabled"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_langchain_tracing(settings: Settings | None = None) -> None:
    """Pass validated Pydantic settings to LangChain's process-level tracer."""
    runtime = settings or get_settings()
    os.environ["LANGCHAIN_TRACING_V2"] = (
        "true" if runtime.langchain_tracing_v2 else "false"
    )
    if runtime.langchain_tracing_v2:
        os.environ["LANGCHAIN_API_KEY"] = runtime.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = runtime.langchain_project
