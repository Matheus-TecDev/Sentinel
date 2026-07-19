from datetime import datetime, timedelta, timezone

import pytest
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import IncidentStatus, ServiceEnvironment
from app.models.incident import Incident
from app.models.service import MonitoredService
from app.repositories.incident_repository import is_open_incident_unique_violation

pytestmark = pytest.mark.integration


def create_service(db: Session, name: str) -> MonitoredService:
    service = MonitoredService(
        name=name,
        environment=ServiceEnvironment.PRODUCTION,
        healthcheck_url=f"https://{name.lower().replace(' ', '-')}.example.test/health",
        owner="Integration Tests",
        is_active=True,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def make_incident(
    service_id: int,
    status: IncidentStatus,
    offset_minutes: int = 0,
) -> Incident:
    started_at = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc) + timedelta(
        minutes=offset_minutes
    )
    return Incident(
        service_id=service_id,
        status=status,
        started_at=started_at,
        resolved_at=started_at + timedelta(minutes=1)
        if status == IncidentStatus.RESOLVED
        else None,
        duration_seconds=60 if status == IncidentStatus.RESOLVED else None,
        reason="Serviço offline",
    )


def test_alembic_is_at_head_and_partial_unique_index_is_valid(
    integration_engine: Engine,
    alembic_config: Config,
) -> None:
    expected_head = ScriptDirectory.from_config(alembic_config).get_current_head()

    with integration_engine.connect() as connection:
        current_revision = MigrationContext.configure(connection).get_current_revision()
        index = connection.execute(
            text(
                """
                SELECT index_record.indisunique AS is_unique,
                       pg_get_expr(index_record.indpred, index_record.indrelid) AS predicate
                FROM pg_class index_class
                JOIN pg_index index_record ON index_record.indexrelid = index_class.oid
                JOIN pg_class table_class ON table_class.oid = index_record.indrelid
                WHERE index_class.relname = 'uq_incidents_service_id_open'
                  AND table_class.relname = 'incidents'
                """
            )
        ).mappings().one()

    assert current_revision == expected_head
    assert expected_head == "0005_unique_open_incident"
    assert index["is_unique"] is True
    predicate = index["predicate"].lower()
    assert "status" in predicate
    assert "open" in predicate
    assert "resolved" not in predicate


def test_unique_open_incident_invariant(db_session: Session) -> None:
    first_service = create_service(db_session, "Payments API")
    second_service = create_service(db_session, "Orders API")
    db_session.add(make_incident(first_service.id, IncidentStatus.OPEN))
    db_session.commit()

    db_session.add(
        make_incident(first_service.id, IncidentStatus.OPEN, offset_minutes=1)
    )
    with pytest.raises(IntegrityError) as raised:
        db_session.commit()
    assert is_open_incident_unique_violation(raised.value)
    db_session.rollback()

    db_session.add_all(
        [
            make_incident(first_service.id, IncidentStatus.RESOLVED, offset_minutes=2),
            make_incident(first_service.id, IncidentStatus.RESOLVED, offset_minutes=3),
            make_incident(second_service.id, IncidentStatus.OPEN),
        ]
    )
    db_session.commit()

    open_counts = dict(
        db_session.execute(
            select(Incident.service_id, func.count(Incident.id))
            .where(Incident.status == IncidentStatus.OPEN)
            .group_by(Incident.service_id)
        ).all()
    )
    resolved_count = db_session.execute(
        select(func.count(Incident.id)).where(
            Incident.service_id == first_service.id,
            Incident.status == IncidentStatus.RESOLVED,
        )
    ).scalar_one()

    assert open_counts == {first_service.id: 1, second_service.id: 1}
    assert resolved_count == 2


def test_resolving_open_incident_allows_later_open_incident(
    db_session: Session,
) -> None:
    service = create_service(db_session, "Recovery API")
    first_incident = make_incident(service.id, IncidentStatus.OPEN)
    db_session.add(first_incident)
    db_session.commit()

    first_incident.status = IncidentStatus.RESOLVED
    first_incident.resolved_at = first_incident.started_at + timedelta(minutes=2)
    first_incident.duration_seconds = 120
    db_session.commit()

    second_incident = make_incident(
        service.id,
        IncidentStatus.OPEN,
        offset_minutes=3,
    )
    db_session.add(second_incident)
    db_session.commit()

    incidents = db_session.execute(
        select(Incident).where(Incident.service_id == service.id)
    ).scalars().all()
    assert len(incidents) == 2
    assert sum(item.status == IncidentStatus.OPEN for item in incidents) == 1
    assert sum(item.status == IncidentStatus.RESOLVED for item in incidents) == 1
