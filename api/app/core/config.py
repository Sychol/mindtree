import json
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="local", alias="APP_ENV")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    database_url: str = Field(default="", alias="DATABASE_URL")

    jwt_secret_key: str = Field(
        default="change-me-in-local-only",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    admin_jwt_expires_minutes: int = Field(default=480, alias="ADMIN_JWT_EXPIRES_MINUTES")
    admin_bootstrap_email: str = Field(default="", alias="ADMIN_BOOTSTRAP_EMAIL")
    admin_bootstrap_password: str = Field(default="", alias="ADMIN_BOOTSTRAP_PASSWORD")
    admin_bootstrap_display_name: str = Field(
        default="\uc6b4\uc601\uc790",
        alias="ADMIN_BOOTSTRAP_DISPLAY_NAME",
    )

    llm_enabled: bool = Field(default=False, alias="LLM_ENABLED")
    llm_provider: str = Field(default="disabled", alias="LLM_PROVIDER")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_timeout_seconds: int = Field(default=5, alias="LLM_TIMEOUT_SECONDS")

    keyword_worker_enabled: bool = Field(default=False, alias="KEYWORD_WORKER_ENABLED")
    keyword_fallback_enabled: bool = Field(default=True, alias="KEYWORD_FALLBACK_ENABLED")
    keyword_worker_interval_seconds: int = Field(
        default=3,
        alias="KEYWORD_WORKER_INTERVAL_SECONDS",
    )
    keyword_worker_batch_size: int = Field(
        default=5,
        alias="KEYWORD_WORKER_BATCH_SIZE",
    )
    display_sse_heartbeat_seconds: int = Field(
        default=15,
        alias="DISPLAY_SSE_HEARTBEAT_SECONDS",
    )
    display_snapshot_interval_seconds: int = Field(
        default=5,
        alias="DISPLAY_SNAPSHOT_INTERVAL_SECONDS",
    )

    cors_origins_raw: str = Field(
        default="http://localhost:5173",
        alias="CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        raw_value = self.cors_origins_raw.strip()
        if raw_value.startswith("["):
            try:
                parsed_value = json.loads(raw_value)
            except json.JSONDecodeError:
                parsed_value = None

            if isinstance(parsed_value, list):
                return [
                    str(origin).strip()
                    for origin in parsed_value
                    if str(origin).strip()
                ]

        return [
            origin.strip()
            for origin in raw_value.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
