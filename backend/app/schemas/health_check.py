from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import HealthStatus


class HealthCheckResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_id: int
    status: HealthStatus
    http_status_code: int | None
    response_time_ms: float | None
    error_message: str | None
    checked_at: datetime
