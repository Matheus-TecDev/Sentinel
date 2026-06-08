from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import HealthStatus, ServiceEnvironment
from app.models.health_check import HealthCheckResult
from app.models.service import MonitoredService
from app.repositories.health_check_repository import HealthCheckRepository
from app.repositories.service_repository import ServiceRepository
from app.schemas.service import ServiceCreate, ServiceDetail, ServiceUpdate, ServiceWithStatus


def serialize_service_with_status(
    service: MonitoredService,
    latest: HealthCheckResult | None = None,
) -> ServiceWithStatus:
    data = ServiceWithStatus.model_validate(service).model_dump()
    if latest is not None:
        data.update(
            {
                "current_status": latest.status,
                "last_http_status_code": latest.http_status_code,
                "last_response_time_ms": latest.response_time_ms,
                "last_checked_at": latest.checked_at,
            }
        )
    return ServiceWithStatus(**data)


class ServiceService:
    def __init__(self) -> None:
        self.services = ServiceRepository()
        self.checks = HealthCheckRepository()

    def list(
        self,
        db: Session,
        q: str | None = None,
        environment: ServiceEnvironment | None = None,
        status_filter: HealthStatus | None = None,
        is_active: bool | None = None,
    ) -> list[ServiceWithStatus]:
        services = self.services.list(db, q=q, environment=environment, is_active=is_active)
        latest = self.checks.latest_by_service(db)
        items = [serialize_service_with_status(service, latest.get(service.id)) for service in services]
        if status_filter is not None:
            items = [item for item in items if item.current_status == status_filter]
        return items

    def get_detail(self, db: Session, service_id: int) -> ServiceDetail:
        service = self._get_or_404(db, service_id)
        latest = self.checks.latest_by_service(db).get(service.id)
        base = serialize_service_with_status(service, latest).model_dump()
        return ServiceDetail(
            **base,
            average_response_time_ms=self.checks.average_response_time(db, service_id=service.id),
            uptime_percent=self.checks.uptime_percent(db, service_id=service.id),
            recent_checks=self.checks.recent_for_service(db, service_id=service.id, limit=50),
            recent_failures=self.checks.recent_failures(db, service_id=service.id, limit=10),
        )

    def create(self, db: Session, payload: ServiceCreate) -> ServiceWithStatus:
        service = self.services.create(db, payload.model_dump())
        return serialize_service_with_status(service)

    def update(self, db: Session, service_id: int, payload: ServiceUpdate) -> ServiceWithStatus:
        service = self._get_or_404(db, service_id)
        data = payload.model_dump(exclude_unset=True)
        service = self.services.update(db, service, data)
        latest = self.checks.latest_by_service(db).get(service.id)
        return serialize_service_with_status(service, latest)

    def set_active(self, db: Session, service_id: int, is_active: bool) -> ServiceWithStatus:
        service = self._get_or_404(db, service_id)
        service = self.services.update(db, service, {"is_active": is_active})
        latest = self.checks.latest_by_service(db).get(service.id)
        return serialize_service_with_status(service, latest)

    def _get_or_404(self, db: Session, service_id: int) -> MonitoredService:
        service = self.services.get(db, service_id)
        if service is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado")
        return service
