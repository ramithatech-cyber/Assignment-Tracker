"""Application settings, loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Student Assignment Tracker"
    debug: bool = False

    # --- Persistence --------------------------------------------------------
    database_url: str = "sqlite:///./assignment_tracker.db"

    # --- Auth ---------------------------------------------------------------
    jwt_secret: str = "insecure-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # --- OpenAI -------------------------------------------------------------
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1"
    openai_timeout: int = 90
    # Rough character budget for the repo bundle handed to the model
    # (~4 chars per token, so 240k chars ~= 60k tokens).
    llm_context_chars: int = 240_000

    # --- GitHub -------------------------------------------------------------
    github_token: str = ""
    github_api: str = "https://api.github.com"

    # --- Guard rails --------------------------------------------------------
    max_repo_size_kb: int = 50_000
    max_files: int = 2_000
    max_file_bytes: int = 1_000_000
    fetch_timeout: int = 60
    linter_timeout: int = 30

    # --- 45-day activity programme -----------------------------------------
    program_days: int = 45
    # Days unlock on their calendar date in THIS timezone, not the server's.
    # Use an IANA name, e.g. Asia/Kolkata.
    program_timezone: str = "UTC"

    # --- CORS ---------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
