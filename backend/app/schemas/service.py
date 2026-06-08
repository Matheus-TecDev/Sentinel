from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import HealthStatus, ServiceEnvironment
from app.schemas.health_check import HealthCheckResultRead


class ServiceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    environment: ServiceEnvironment
    healthcheck_url: str = Field(..., min_length=8, max_length=2048)
    owner: str = Field(..., min_length=2, max_length=120)
    is_active: bool = True

    @field_validator("healthcheck_url")
    @classmethod
    def validate_healthcheck_url(cls, value: str) -> str:
        normalized = value.strip()
        if not (normalized.startswith("http://") or normalized.startswith("https://")):
            raise ValueError("healthcheck_url must start with http:// or https://")
        return normalized


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    environment: ServiceEnvironment | None = None
    healthcheck_url: str | None = Field(default=None, min_length=8, max_length=2048)
    owner: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None

    @field_validator("healthcheck_url")
    @classmethod
    def validate_optional_healthcheck_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not (normalized.startswith("http://") or normalized.startswith("https://")):
            raise ValueError("healthcheck_url must start with http:// or https://")
        return normalized


class ServiceActivationUpdate(BaseModel):
    is_active: bool


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    environment: ServiceEnvironment
    healthcheck_url: str
    owner: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ServiceWithStatus(ServiceRead):
    current_status: HealthStatus | None = None
    last_http_status_code: int | None = None
    last_response_time_ms: float | None = None
    last_checked_at: datetime | None = None


class ServiceDetail(ServiceWithStatus):
    average_response_time_ms: float | None
    uptime_percent: float
    recent_checks: list[HealthCheckResultRead]
    recent_failures: list[HealthCheckResultRead]
