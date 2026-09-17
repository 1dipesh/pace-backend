from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Pace API"
    app_env: str = "local"
    app_version: str = "0.10.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://pace:pace@localhost:5432/pace"
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    auth_jwt_algorithms: list[str] = ["ES256", "RS256"]
    auth_clock_skew_seconds: int = 30
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    ai_beta_unlimited: bool = True
    ai_requests_per_minute: int = 10
    ai_max_input_chars: int = 2000
    ai_max_output_tokens: int = 700
    ai_history_messages: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", "auth_jwt_algorithms", mode="before")
    @classmethod
    def parse_string_list(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def supabase_jwt_issuer(self) -> str | None:
        if not self.supabase_url:
            return None
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def supabase_jwks_url(self) -> str | None:
        issuer = self.supabase_jwt_issuer
        if not issuer:
            return None
        return f"{issuer}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
