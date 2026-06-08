from pydantic import BaseModel

from app.schemas.health_check import HealthCheckResultRead
from app.schemas.service import ServiceWithStatus


class DashboardSummary(BaseModel):
    total_services: int
    online_services: int
    offline_services: int
    degraded_services: int
    inactive_services: int
    average_response_time_ms: float | None
    overall_uptime_percent: float
    recent_failures: list[HealthCheckResultRead]
    services: list[ServiceWithStatus]
