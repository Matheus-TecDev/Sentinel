from __future__ import annotations

from builtins import list as builtin_list

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ServiceEnvironment
from app.models.service import MonitoredService


class ServiceRepository:
    def get(self, db: Session, service_id: int) -> MonitoredService | None:
        return db.get(MonitoredService, service_id)

    def list(
        self,
        db: Session,
        q: str | None = None,
        environment: ServiceEnvironment | None = None,
        is_active: bool | None = None,
    ) -> list[MonitoredService]:
        statement = select(MonitoredService)

        if q:
            statement = statement.where(MonitoredService.name.ilike(f"%{q.strip()}%"))

        if environment:
            statement = statement.where(MonitoredService.environment == environment)

        if is_active is not None:
            statement = statement.where(MonitoredService.is_active == is_active)

        statement = statement.order_by(MonitoredService.name.asc())

        return builtin_list(db.execute(statement).scalars().all())

    def list_active(self, db: Session) -> list[MonitoredService]:
        statement = select(MonitoredService).where(MonitoredService.is_active.is_(True))
        return builtin_list(db.execute(statement).scalars().all())

    def create(self, db: Session, data: dict) -> MonitoredService:
        service = MonitoredService(**data)
        db.add(service)
        db.commit()
        db.refresh(service)
        return service

    def update(
        self,
        db: Session,
        service: MonitoredService,
        data: dict,
    ) -> MonitoredService:
        for key, value in data.items():
            setattr(service, key, value)

        db.add(service)
        db.commit()
        db.refresh(service)
        return service