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
    
    # Model provider toggle: 0 = Gemini (default), 1 = Groq
    MODEL_PROVIDER: int = Field(default=0)

    # Credentials & API Keys
    GEMINI_API_KEY: str | None = Field(default=None)
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash")
    GROQ_API_KEY: str | None = Field(default=None)
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
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
        """
        Normalizes environment variables that can be specified as strings or booleans.
        Converts string representations (e.g., 'true', '1', 'off') into Python boolean types
        so that validation succeeds regardless of the format specified in .env files.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value
    
    # CORS
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"]
    )

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
