from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import IncidentStatus
from app.models.incident import Incident
from app.models.service import MonitoredService

OPEN_INCIDENT_UNIQUE_INDEX = "uq_incidents_service_id_open"


def is_open_incident_unique_violation(error: IntegrityError) -> bool:
    diagnostic = getattr(error.orig, "diag", None)
    return getattr(diagnostic, "constraint_name", None) == OPEN_INCIDENT_UNIQUE_INDEX


class IncidentRepository:
    def create(self, db: Session, data: dict) -> Incident:
        incident = Incident(**data)
        db.add(incident)
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            if not is_open_incident_unique_violation(error):
                raise
            competing_incident = self.open_for_service(db, data["service_id"])
            if competing_incident is None:
                raise
            return competing_incident
        db.refresh(incident)
        return incident

    def create_in_transaction(self, db: Session, data: dict) -> Incident:
        incident = Incident(**data)
        try:
            with db.begin_nested():
                db.add(incident)
                db.flush()
        except IntegrityError as error:
            if not is_open_incident_unique_violation(error):
                raise
            competing_incident = self.open_for_service(db, data["service_id"])
            if competing_incident is None:
                raise
            return competing_incident
        db.refresh(incident)
        return incident

    def update(self, db: Session, incident: Incident, data: dict) -> Incident:
        for key, value in data.items():
            setattr(incident, key, value)
        db.add(incident)
        db.commit()
        db.refresh(incident)
        return incident

    def update_in_transaction(self, db: Session, incident: Incident, data: dict) -> Incident:
        for key, value in data.items():
            setattr(incident, key, value)
        db.add(incident)
        db.flush()
        db.refresh(incident)
        return incident

    def open_for_service(self, db: Session, service_id: int) -> Incident | None:
        statement = (
            select(Incident)
            .where(Incident.service_id == service_id, Incident.status == IncidentStatus.OPEN)
            .order_by(desc(Incident.started_at))
            .limit(1)
        )
        return db.execute(statement).scalars().first()

    def list(
        self,
        db: Session,
        status: IncidentStatus | None = None,
        service_id: int | None = None,
        limit: int = 50,
    ) -> list[Incident]:
        statement = select(Incident).order_by(desc(Incident.started_at)).limit(limit)
        if status is not None:
            statement = statement.where(Incident.status == status)
        if service_id is not None:
            statement = statement.where(Incident.service_id == service_id)
        return list(db.execute(statement).scalars().all())

    def list_for_service(self, db: Session, service_id: int, limit: int = 50) -> list[Incident]:
        return self.list(db, service_id=service_id, limit=limit)

    def count_open(self, db: Session) -> int:
        statement = select(func.count(Incident.id)).where(Incident.status == IncidentStatus.OPEN)
        return int(db.execute(statement).scalar_one())

    def recent_with_service(self, db: Session, limit: int = 10) -> list[tuple[Incident, str]]:
        statement = (
            select(Incident, MonitoredService.name)
            .join(MonitoredService, MonitoredService.id == Incident.service_id)
            .order_by(desc(Incident.started_at))
            .limit(limit)
        )
        return list(db.execute(statement).all())

    def count_by_service_since(self, db: Session, since: datetime, limit: int = 5) -> list[tuple[int, str, int]]:
        statement = (
            select(Incident.service_id, MonitoredService.name, func.count(Incident.id).label("incident_count"))
            .join(MonitoredService, MonitoredService.id == Incident.service_id)
            .where(Incident.started_at >= since)
            .group_by(Incident.service_id, MonitoredService.name)
            .order_by(desc("incident_count"), MonitoredService.name.asc())
            .limit(limit)
        )
        return [(service_id, name, count) for service_id, name, count in db.execute(statement).all()]
