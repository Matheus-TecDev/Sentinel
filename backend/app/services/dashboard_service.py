from sqlalchemy.orm import Session

from app.core.enums import HealthStatus, NotificationStatus
from app.core.periods import period_start
from app.repositories.health_check_repository import HealthCheckRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.notification_repository import NotificationLogRepository
from app.repositories.service_repository import ServiceRepository
from app.schemas.alert import NotificationLogWithService
from app.schemas.dashboard import DashboardSummary, ServiceInstabilitySummary, ServiceResponseSummary
from app.schemas.incident import IncidentWithService
from app.services.alert_service import mask_target
from app.services.service_service import serialize_service_with_status


class DashboardService:
    def __init__(self) -> None:
        self.services = ServiceRepository()
        self.checks = HealthCheckRepository()
        self.incidents = IncidentRepository()
        self.notifications = NotificationLogRepository()

    def summary(self, db: Session) -> DashboardSummary:
        services = self.services.list(db)
        latest = self.checks.latest_by_service(db)
        serialized = [serialize_service_with_status(service, latest.get(service.id)) for service in services]
        active_items = [item for item in serialized if item.is_active]
        last_24h = period_start("24h")
        incident_counts = {
            service_id: count
            for service_id, _name, count in self.incidents.count_by_service_since(db, last_24h, limit=50)
        }
        recent_incidents = [
            IncidentWithService.model_validate({**incident.__dict__, "service_name": service_name})
            for incident, service_name in self.incidents.recent_with_service(db, limit=10)
        ]
        unstable_services = [
            ServiceInstabilitySummary(
                service_id=service_id,
                service_name=name,
                unhealthy_checks=unhealthy,
                failure_checks=failures,
                incident_count=incident_counts.get(service_id, 0),
            )
            for service_id, name, unhealthy, failures in self.checks.unstable_services_since(db, last_24h, limit=5)
        ]
        slowest_services = [
            ServiceResponseSummary(
                service_id=service_id,
                service_name=name,
                average_response_time_ms=average,
            )
            for service_id, name, average in self.checks.slowest_services_since(db, last_24h, limit=5)
        ]
        recent_notifications = [
            NotificationLogWithService.model_validate(
                {
                    **notification.__dict__,
                    "masked_target": mask_target(notification.target),
                    "service_name": service_name,
                }
            )
            for notification, service_name in self.notifications.recent_with_service(db, limit=10)
        ]
        failed_notifications = [
            NotificationLogWithService.model_validate(
                {
                    **notification.__dict__,
                    "masked_target": mask_target(notification.target),
                    "service_name": service_name,
                }
            )
            for notification, service_name in self.notifications.recent_with_service(
                db, limit=10, status=NotificationStatus.FAILED
            )
        ]

        return DashboardSummary(
            total_services=len(services),
            online_services=sum(1 for item in active_items if item.current_status == HealthStatus.ONLINE),
            offline_services=sum(1 for item in active_items if item.current_status == HealthStatus.OFFLINE),
            degraded_services=sum(1 for item in active_items if item.current_status == HealthStatus.DEGRADED),
            inactive_services=sum(1 for item in serialized if not item.is_active),
            average_response_time_ms=self.checks.average_response_time(db),
            overall_uptime_percent=self.checks.uptime_percent(db),
            open_incidents=self.incidents.count_open(db),
            failures_last_24h=self.checks.failure_count(db, since=last_24h),
            recent_failures=self.checks.recent_failures(db, limit=10),
            recent_incidents=recent_incidents,
            recent_notifications=recent_notifications,
            failed_notifications=failed_notifications,
            unstable_services=unstable_services,
            slowest_services=slowest_services,
            services=serialized,
        )
