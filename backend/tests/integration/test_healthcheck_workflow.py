import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Barrier, Lock

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.enums import (
    HealthStatus,
    IncidentStatus,
    NotificationEventType,
    ServiceEnvironment,
)
from app.models.health_check import HealthCheckResult
from app.models.incident import Incident
from app.models.service import MonitoredService
from app.repositories.health_check_repository import HealthCheckRepository
from app.repositories.incident_repository import (
    IncidentCreationResult,
    IncidentRepository,
    is_open_incident_unique_violation,
)
from app.services.incident_service import IncidentService, IncidentTransition
from app.workers.healthcheck_worker import persist_check_and_sync_incident

pytestmark = pytest.mark.integration


class RecordingNotificationService:
    def __init__(self) -> None:
        self._lock = Lock()
        self.decisions: list[tuple[int, NotificationEventType]] = []

    async def notify_incident_event(
        self,
        _db: Session,
        incident: Incident,
        event_type: NotificationEventType,
    ) -> list:
        with self._lock:
            self.decisions.append((incident.id, event_type))
        return []


class FailingIncidentService:
    def sync_from_check(
        self,
        _db: Session,
        _check: HealthCheckResult,
    ) -> None:
        raise RuntimeError("incident synchronization failed")


class UnrelatedIntegrityIncidentService:
    def __init__(self) -> None:
        self.incidents = IncidentRepository()

    def sync_from_check(
        self,
        db: Session,
        check: HealthCheckResult,
    ) -> None:
        self.incidents.create_in_transaction(
            db,
            {
                "service_id": check.service_id + 10000,
                "status": IncidentStatus.OPEN,
                "started_at": check.checked_at,
                "reason": "Serviço offline",
            },
        )


def create_service(db: Session, name: str = "Payments API") -> MonitoredService:
    service = MonitoredService(
        name=name,
        environment=ServiceEnvironment.PRODUCTION,
        healthcheck_url="https://payments.example.test/health",
        owner="Integration Tests",
        is_active=True,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def health_check_data(service_id: int) -> dict:
    return {
        "service_id": service_id,
        "status": HealthStatus.OFFLINE,
        "http_status_code": None,
        "response_time_ms": None,
        "error_message": "Connection refused",
    }


def incident_service(repository: IncidentRepository | None = None) -> IncidentService:
    service = IncidentService(Settings(INCIDENT_FAILURE_THRESHOLD=1, _env_file=None))
    if repository is not None:
        service.incidents = repository
    return service


def run_workflow(
    db: Session,
    service_id: int,
    incidents,
    notifications: RecordingNotificationService,
) -> tuple[HealthCheckResult, IncidentTransition | None]:
    return asyncio.run(
        persist_check_and_sync_incident(
            db,
            health_check_data(service_id),
            HealthCheckRepository(),
            incidents,
            notifications,
        )
    )


def persisted_counts(db: Session) -> tuple[int, int]:
    checks = db.execute(select(func.count(HealthCheckResult.id))).scalar_one()
    incidents = db.execute(select(func.count(Incident.id))).scalar_one()
    return checks, incidents


def test_successful_health_check_and_incident_commit_together(
    db_session: Session,
    integration_session_factory: sessionmaker[Session],
) -> None:
    service = create_service(db_session)
    notifications = RecordingNotificationService()

    check, transition = run_workflow(
        db_session,
        service.id,
        incident_service(),
        notifications,
    )

    assert check.id is not None
    assert transition is not None
    assert transition.event_type == NotificationEventType.INCIDENT_OPENED
    with integration_session_factory() as verification:
        assert persisted_counts(verification) == (1, 1)
    assert notifications.decisions == [
        (transition.incident.id, NotificationEventType.INCIDENT_OPENED)
    ]


def test_incident_synchronization_failure_rolls_back_health_check(
    db_session: Session,
    integration_session_factory: sessionmaker[Session],
) -> None:
    service = create_service(db_session)
    notifications = RecordingNotificationService()

    with pytest.raises(RuntimeError, match="incident synchronization failed"):
        run_workflow(
            db_session,
            service.id,
            FailingIncidentService(),
            notifications,
        )

    with integration_session_factory() as verification:
        assert persisted_counts(verification) == (0, 0)
    assert notifications.decisions == []


def test_commit_failure_leaves_no_partial_persisted_state(
    db_session: Session,
    integration_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = create_service(db_session)
    notifications = RecordingNotificationService()

    def fail_commit() -> None:
        raise RuntimeError("commit failed")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="commit failed"):
        run_workflow(
            db_session,
            service.id,
            incident_service(),
            notifications,
        )

    with integration_session_factory() as verification:
        assert persisted_counts(verification) == (0, 0)
    assert notifications.decisions == []


def test_unrelated_integrity_error_rolls_back_and_propagates(
    db_session: Session,
    integration_session_factory: sessionmaker[Session],
) -> None:
    service = create_service(db_session)
    notifications = RecordingNotificationService()

    with pytest.raises(IntegrityError) as raised:
        run_workflow(
            db_session,
            service.id,
            UnrelatedIntegrityIncidentService(),
            notifications,
        )

    assert not is_open_incident_unique_violation(raised.value)
    with integration_session_factory() as verification:
        assert persisted_counts(verification) == (0, 0)
    assert notifications.decisions == []


class CoordinatedIncidentRepository(IncidentRepository):
    def __init__(self, barrier: Barrier) -> None:
        self.barrier = barrier
        self.open_calls = 0
        self.creation_result: IncidentCreationResult | None = None

    def open_for_service(self, db: Session, service_id: int) -> Incident | None:
        incident = super().open_for_service(db, service_id)
        self.open_calls += 1
        if self.open_calls == 1:
            self.barrier.wait(timeout=5)
        return incident

    def create_in_transaction(
        self,
        db: Session,
        data: dict,
    ) -> IncidentCreationResult:
        result = super().create_in_transaction(db, data)
        self.creation_result = result
        return result


@dataclass(frozen=True)
class WorkerOutcome:
    check_id: int
    transition: IncidentTransition | None
    creation_result: IncidentCreationResult
    session_usable: bool


def test_concurrent_workers_persist_both_checks_and_one_incident(
    db_session: Session,
    integration_session_factory: sessionmaker[Session],
) -> None:
    service = create_service(db_session)
    barrier = Barrier(2, timeout=5)
    notifications = RecordingNotificationService()

    def execute_worker() -> WorkerOutcome:
        repository = CoordinatedIncidentRepository(barrier)
        with integration_session_factory() as worker_session:
            worker_session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            check, transition = run_workflow(
                worker_session,
                service.id,
                incident_service(repository),
                notifications,
            )
            session_usable = worker_session.execute(text("SELECT 1")).scalar_one() == 1
            assert repository.creation_result is not None
            return WorkerOutcome(
                check_id=check.id,
                transition=transition,
                creation_result=repository.creation_result,
                session_usable=session_usable,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(execute_worker) for _ in range(2)]
        outcomes = [future.result(timeout=15) for future in futures]

    with integration_session_factory() as verification:
        checks = verification.execute(
            select(HealthCheckResult).where(
                HealthCheckResult.service_id == service.id
            )
        ).scalars().all()
        open_incidents = verification.execute(
            select(Incident).where(
                Incident.service_id == service.id,
                Incident.status == IncidentStatus.OPEN,
            )
        ).scalars().all()

    winner = next(outcome for outcome in outcomes if outcome.creation_result.created)
    loser = next(outcome for outcome in outcomes if not outcome.creation_result.created)
    assert len(checks) == 2
    assert len(open_incidents) == 1
    assert {item.id for item in checks} == {item.check_id for item in outcomes}
    assert winner.transition is not None
    assert winner.transition.event_type == NotificationEventType.INCIDENT_OPENED
    assert loser.transition is None
    assert loser.creation_result.incident.id == winner.creation_result.incident.id
    assert all(outcome.session_usable for outcome in outcomes)
    assert notifications.decisions == [
        (open_incidents[0].id, NotificationEventType.INCIDENT_OPENED)
    ]
