from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.enums import HealthStatus, IncidentStatus, NotificationEventType
from app.models.health_check import HealthCheckResult
from app.models.incident import Incident
from app.repositories.health_check_repository import HealthCheckRepository
from app.repositories.incident_repository import IncidentRepository


def incident_reason(status: HealthStatus) -> str:
    if status == HealthStatus.OFFLINE:
        return "Serviço offline"
    if status == HealthStatus.DEGRADED:
        return "Serviço degradado"
    return "Serviço recuperado"


def duration_seconds(started_at: datetime, resolved_at: datetime) -> int:
    return max(0, int((resolved_at - started_at).total_seconds()))


def concrete_error_message(error_message: str | None) -> str | None:
    if error_message is None or not error_message.strip():
        return None
    return error_message


@dataclass(frozen=True)
class IncidentTransition:
    incident: Incident
    event_type: NotificationEventType | None


class IncidentService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.checks = HealthCheckRepository()
        self.incidents = IncidentRepository()

    def sync_from_check(self, db: Session, check: HealthCheckResult) -> IncidentTransition | None:
        open_incident = self.incidents.open_for_service(db, check.service_id)

        if check.status in (HealthStatus.OFFLINE, HealthStatus.DEGRADED):
            error_message = concrete_error_message(check.error_message)
            if open_incident:
                data = {"last_error_message": error_message} if error_message is not None else {}
                incident = self.incidents.update(db, open_incident, data)
                return IncidentTransition(incident=incident, event_type=None)
            unhealthy_count = self.checks.consecutive_unhealthy_count(
                db,
                service_id=check.service_id,
                limit=self.settings.INCIDENT_FAILURE_THRESHOLD,
            )
            if unhealthy_count < self.settings.INCIDENT_FAILURE_THRESHOLD:
                return None
            incident = self.incidents.create(
                db,
                {
                    "service_id": check.service_id,
                    "status": IncidentStatus.OPEN,
                    "started_at": check.checked_at,
                    "reason": incident_reason(check.status),
                    "last_error_message": error_message,
                },
            )
            return IncidentTransition(incident=incident, event_type=NotificationEventType.INCIDENT_OPENED)

        if check.status == HealthStatus.ONLINE and open_incident:
            incident = self.incidents.update(
                db,
                open_incident,
                {
                    "status": IncidentStatus.RESOLVED,
                    "resolved_at": check.checked_at,
                    "duration_seconds": duration_seconds(open_incident.started_at, check.checked_at),
                },
            )
            return IncidentTransition(incident=incident, event_type=NotificationEventType.INCIDENT_RESOLVED)

        return None
