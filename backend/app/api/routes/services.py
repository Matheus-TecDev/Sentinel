from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import operator_access, viewer_access
from app.core.enums import HealthStatus, ServiceEnvironment
from app.db.session import get_db
from app.models.user import User
from app.repositories.health_check_repository import HealthCheckRepository
from app.schemas.health_check import HealthCheckResultRead
from app.schemas.service import ServiceActivationUpdate, ServiceCreate, ServiceDetail, ServiceUpdate, ServiceWithStatus
from app.services.service_service import ServiceService

router = APIRouter(prefix="/services", tags=["services"])
service_service = ServiceService()
health_check_repository = HealthCheckRepository()


@router.get("", response_model=list[ServiceWithStatus])
def list_services(
    q: str | None = Query(default=None),
    environment: ServiceEnvironment | None = Query(default=None),
    status: HealthStatus | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(viewer_access),
) -> list[ServiceWithStatus]:
    return service_service.list(db, q=q, environment=environment, status_filter=status, is_active=is_active)


@router.post("", response_model=ServiceWithStatus, status_code=201)
def create_service(
    payload: ServiceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(operator_access),
) -> ServiceWithStatus:
    return service_service.create(db, payload)


@router.get("/checks/history", response_model=list[HealthCheckResultRead])
def checks_history(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(viewer_access),
) -> list[HealthCheckResultRead]:
    return health_check_repository.history(db, limit=limit)


@router.get("/checks/failures", response_model=list[HealthCheckResultRead])
def checks_failures(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(viewer_access),
) -> list[HealthCheckResultRead]:
    return health_check_repository.recent_failures(db, limit=limit)


@router.get("/{service_id}", response_model=ServiceDetail)
def get_service(
    service_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(viewer_access),
) -> ServiceDetail:
    return service_service.get_detail(db, service_id)


@router.put("/{service_id}", response_model=ServiceWithStatus)
def update_service(
    service_id: int,
    payload: ServiceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(operator_access),
) -> ServiceWithStatus:
    return service_service.update(db, service_id, payload)


@router.patch("/{service_id}/activation", response_model=ServiceWithStatus)
def set_service_activation(
    service_id: int,
    payload: ServiceActivationUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(operator_access),
) -> ServiceWithStatus:
    return service_service.set_active(db, service_id, payload.is_active)


@router.get("/{service_id}/checks", response_model=list[HealthCheckResultRead])
def service_checks(
    service_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(viewer_access),
) -> list[HealthCheckResultRead]:
    service_service.get_detail(db, service_id)
    return health_check_repository.recent_for_service(db, service_id=service_id, limit=limit)
