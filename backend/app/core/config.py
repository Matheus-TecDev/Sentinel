from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "Sentinel"
    ENVIRONMENT: str = "local"
    API_PREFIX: str = "/api"

    DATABASE_URL: str = "postgresql+psycopg://sentinel:sentinel_dev_password@localhost:5432/sentinel"

    JWT_SECRET_KEY: str = Field(default="change-this-development-secret")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    BACKEND_CORS_ORIGINS: str = (
        "http://localhost,"
        "http://127.0.0.1,"
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )

    HEALTHCHECK_INTERVAL_SECONDS: int = 60
    HEALTHCHECK_TIMEOUT_SECONDS: float = 5.0
    DEGRADED_RESPONSE_TIME_MS: int = 1000
    INCIDENT_FAILURE_THRESHOLD: int = Field(default=3, ge=1)
    ENABLE_HEALTHCHECK_WORKER: bool = True

    INITIAL_ADMIN_NAME: str = "Sentinel Admin"
    INITIAL_ADMIN_EMAIL: str = "admin@sentinel.local"
    INITIAL_ADMIN_PASSWORD: str = "ChangeMe123!"

    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
