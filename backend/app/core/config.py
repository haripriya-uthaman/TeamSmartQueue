from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Ticket Quality Auditor"
    API_V1_STR: str = "/api/v1"
    
    # Environment config
    APP_ENV: str = Field(default="development")
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")
    
    # Credentials & API Keys
    GEMINI_API_KEY: str | None = Field(default=None)
    GITHUB_TOKEN: str | None = Field(default=None)
    GITHUB_OWNER: str | None = Field(default=None)
    GITHUB_REPO: str | None = Field(default=None)

    # LangSmith / LangChain tracing
    LANGSMITH_API_KEY: str | None = Field(default=None)
    LANGSMITH_PROJECT: str = Field(default="team-smart-queue")
    LANGSMITH_TRACING: bool = Field(default=True)
    LANGCHAIN_TRACING_V2: bool = Field(default=True)

    @field_validator("DEBUG", "LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2", mode="before")
    @classmethod
    def parse_boolish_env(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value
    
    # Database Configuration
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./ticket_auditor.db")
    CHROMA_DB_PATH: str = Field(default="./chroma_db")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
