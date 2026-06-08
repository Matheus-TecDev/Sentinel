from sqlalchemy.orm import Session

from app.core.enums import HealthStatus
from app.repositories.health_check_repository import HealthCheckRepository
from app.repositories.service_repository import ServiceRepository
from app.schemas.dashboard import DashboardSummary
from app.services.service_service import serialize_service_with_status


class DashboardService:
    def __init__(self) -> None:
        self.services = ServiceRepository()
        self.checks = HealthCheckRepository()

    def summary(self, db: Session) -> DashboardSummary:
        services = self.services.list(db)
        latest = self.checks.latest_by_service(db)
        serialized = [serialize_service_with_status(service, latest.get(service.id)) for service in services]
        active_items = [item for item in serialized if item.is_active]

        return DashboardSummary(
            total_services=len(services),
            online_services=sum(1 for item in active_items if item.current_status == HealthStatus.ONLINE),
            offline_services=sum(1 for item in active_items if item.current_status == HealthStatus.OFFLINE),
            degraded_services=sum(1 for item in active_items if item.current_status == HealthStatus.DEGRADED),
            inactive_services=sum(1 for item in serialized if not item.is_active),
            average_response_time_ms=self.checks.average_response_time(db),
            overall_uptime_percent=self.checks.uptime_percent(db),
            recent_failures=self.checks.recent_failures(db, limit=10),
            services=serialized,
        )
