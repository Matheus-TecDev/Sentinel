import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.enums import HealthStatus, IncidentStatus, NotificationEventType
from app.models.health_check import HealthCheckResult
from app.models.incident import Incident
from app.repositories.health_check_repository import HealthCheckRepository
from app.repositories.incident_repository import IncidentCreationResult, IncidentRepository
from app.services.incident_service import IncidentService, IncidentTransition
from app.workers.healthcheck_worker import persist_check_and_sync_incident

CHECKED_AT = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)


class ConstraintDiagnostic:
    def __init__(self, constraint_name: str) -> None:
        self.constraint_name = constraint_name


class DatabaseError(Exception):
    def __init__(self, constraint_name: str) -> None:
        self.diag = ConstraintDiagnostic(constraint_name)


def make_integrity_error(constraint_name: str) -> IntegrityError:
    return IntegrityError(
        "insert into incidents",
        {},
        DatabaseError(constraint_name),
    )


class FakeSession:
    def __init__(self, commit_error: Exception | None = None) -> None:
        self.commit_error = commit_error
        self.pending: list[object] = []
        self.persisted: list[object] = []
        self.events: list[str] = []
        self.commit_calls = 0
        self.rollback_calls = 0

    def commit(self) -> None:
        self.events.append("commit")
        self.commit_calls += 1
        if self.commit_error is not None:
            raise self.commit_error
        self.persisted.extend(self.pending)
        self.pending.clear()

    def rollback(self) -> None:
        self.events.append("rollback")
        self.rollback_calls += 1
        self.pending.clear()


class FakeCheckRepository:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.create_calls = 0

    def create(self, db: FakeSession, result: dict) -> HealthCheckResult:
        self.create_calls += 1
        db.events.append("check")
        if self.error is not None:
            raise self.error
        check = HealthCheckResult(id=1, **result)
        db.pending.append("check")
        return check


class FakeFlushSession:
    def __init__(self) -> None:
        self.add_calls = 0
        self.flush_calls = 0
        self.refresh_calls = 0
        self.commit_calls = 0

    def add(self, _item: object) -> None:
        self.add_calls += 1

    def flush(self) -> None:
        self.flush_calls += 1

    def refresh(self, _item: object) -> None:
        self.refresh_calls += 1

    def commit(self) -> None:
        self.commit_calls += 1


class FakeIncidentService:
    def __init__(self, operation: str, error: Exception | None = None) -> None:
        self.operation = operation
        self.error = error
        self.sync_calls = 0

    def sync_from_check(
        self,
        db: FakeSession,
        check: HealthCheckResult,
    ) -> IncidentTransition | None:
        self.sync_calls += 1
        db.events.append(f"incident:{self.operation}")
        if self.error is not None:
            raise self.error
        db.pending.append(f"incident:{self.operation}")
        if self.operation == "update":
            return IncidentTransition(
                incident=Incident(
                    id=1,
                    service_id=check.service_id,
                    status=IncidentStatus.OPEN,
                    reason="Serviço offline",
                ),
                event_type=None,
            )
        event_type = (
            NotificationEventType.INCIDENT_RESOLVED
            if self.operation == "resolve"
            else NotificationEventType.INCIDENT_OPENED
        )
        status = IncidentStatus.RESOLVED if self.operation == "resolve" else IncidentStatus.OPEN
        return IncidentTransition(
            incident=Incident(
                id=1,
                service_id=check.service_id,
                status=status,
                reason="Serviço offline",
            ),
            event_type=event_type,
        )


class FakeNotificationService:
    def __init__(self) -> None:
        self.calls: list[tuple[Incident, NotificationEventType]] = []

    async def notify_incident_event(
        self,
        db: FakeSession,
        incident: Incident,
        event_type: NotificationEventType,
    ) -> list:
        assert db.commit_calls == 1
        db.events.append("notify")
        self.calls.append((incident, event_type))
        return []


def make_result(status: HealthStatus = HealthStatus.OFFLINE) -> dict:
    return {
        "service_id": 1,
        "status": status,
        "http_status_code": None,
        "response_time_ms": None,
        "error_message": "Connection refused",
        "checked_at": CHECKED_AT,
    }


def run_workflow(
    db: FakeSession,
    check_repository: FakeCheckRepository,
    incident_service,
    notification_service: FakeNotificationService,
    status: HealthStatus = HealthStatus.OFFLINE,
) -> tuple[HealthCheckResult, IncidentTransition | None]:
    return asyncio.run(
        persist_check_and_sync_incident(
            db,
            make_result(status),
            check_repository,
            incident_service,
            notification_service,
        )
    )


def test_health_check_repository_flushes_without_committing() -> None:
    db = FakeFlushSession()

    HealthCheckRepository().create(db, make_result())

    assert db.add_calls == 1
    assert db.flush_calls == 1
    assert db.refresh_calls == 1
    assert db.commit_calls == 0


@pytest.mark.parametrize(
    ("operation", "status", "expected_event"),
    [
        ("create", HealthStatus.OFFLINE, NotificationEventType.INCIDENT_OPENED),
        ("update", HealthStatus.DEGRADED, None),
        ("resolve", HealthStatus.ONLINE, NotificationEventType.INCIDENT_RESOLVED),
    ],
)
def test_check_and_incident_transition_commit_together(
    operation: str,
    status: HealthStatus,
    expected_event: NotificationEventType | None,
) -> None:
    db = FakeSession()
    checks = FakeCheckRepository()
    incidents = FakeIncidentService(operation)
    notifications = FakeNotificationService()

    _check, transition = run_workflow(
        db,
        checks,
        incidents,
        notifications,
        status,
    )

    assert db.persisted == ["check", f"incident:{operation}"]
    assert db.commit_calls == 1
    assert db.rollback_calls == 0
    assert transition is not None
    assert transition.event_type == expected_event


def test_incident_failure_rolls_back_health_check_and_sends_no_notification() -> None:
    db = FakeSession()
    checks = FakeCheckRepository()
    incidents = FakeIncidentService("create", RuntimeError("incident write failed"))
    notifications = FakeNotificationService()

    with pytest.raises(RuntimeError, match="incident write failed"):
        run_workflow(db, checks, incidents, notifications)

    assert db.persisted == []
    assert db.pending == []
    assert db.commit_calls == 0
    assert db.rollback_calls == 1
    assert notifications.calls == []


def test_health_check_failure_skips_incident_sync_and_notification() -> None:
    db = FakeSession()
    checks = FakeCheckRepository(RuntimeError("check write failed"))
    incidents = FakeIncidentService("create")
    notifications = FakeNotificationService()

    with pytest.raises(RuntimeError, match="check write failed"):
        run_workflow(db, checks, incidents, notifications)

    assert incidents.sync_calls == 0
    assert db.commit_calls == 0
    assert db.rollback_calls == 1
    assert notifications.calls == []


def test_notification_runs_only_after_successful_outer_commit() -> None:
    db = FakeSession()
    notifications = FakeNotificationService()

    run_workflow(
        db,
        FakeCheckRepository(),
        FakeIncidentService("create"),
        notifications,
    )

    assert db.events == ["check", "incident:create", "commit", "notify"]
    assert len(notifications.calls) == 1


def test_outer_commit_failure_rolls_back_and_sends_no_notification() -> None:
    db = FakeSession(commit_error=RuntimeError("commit failed"))
    notifications = FakeNotificationService()

    with pytest.raises(RuntimeError, match="commit failed"):
        run_workflow(
            db,
            FakeCheckRepository(),
            FakeIncidentService("create"),
            notifications,
        )

    assert db.persisted == []
    assert db.pending == []
    assert db.commit_calls == 1
    assert db.rollback_calls == 1
    assert notifications.calls == []


class FakeSavepoint:
    def __init__(self, db: "FakeSavepointSession") -> None:
        self.db = db
        self.start = len(db.pending)

    def __enter__(self) -> "FakeSavepoint":
        self.db.begin_nested_calls += 1
        return self

    def __exit__(self, exc_type, _exc, _traceback) -> bool:
        if exc_type is not None:
            del self.db.pending[self.start :]
            self.db.savepoint_rollback_calls += 1
        return False


class FakeSavepointSession(FakeSession):
    def __init__(self, flush_error: IntegrityError | None = None) -> None:
        super().__init__()
        self.flush_error = flush_error
        self.begin_nested_calls = 0
        self.savepoint_rollback_calls = 0
        self.flush_calls = 0

    def begin_nested(self) -> FakeSavepoint:
        return FakeSavepoint(self)

    def add(self, item: object) -> None:
        self.pending.append(item)

    def flush(self) -> None:
        self.flush_calls += 1
        if self.flush_error is not None:
            raise self.flush_error

    def refresh(self, _item: object) -> None:
        pass


class CompetingIncidentRepository(IncidentRepository):
    def __init__(self, competing_incident: Incident) -> None:
        self.competing_incident = competing_incident

    def open_for_service(self, _db, _service_id: int) -> Incident:
        return self.competing_incident


class NoOpenIncidentRepository(IncidentRepository):
    def open_for_service(self, _db, _service_id: int) -> None:
        return None


class SequentialRaceIncidentRepository(CompetingIncidentRepository):
    def __init__(self, competing_incident: Incident) -> None:
        super().__init__(competing_incident)
        self.open_calls = 0

    def open_for_service(self, _db, _service_id: int) -> Incident | None:
        self.open_calls += 1
        return None if self.open_calls == 1 else self.competing_incident


class ThresholdHealthCheckRepository:
    def consecutive_unhealthy_count(
        self,
        _db,
        service_id: int,
        limit: int,
    ) -> int:
        del service_id
        return limit


def make_incident_service(repository: IncidentRepository) -> IncidentService:
    service = IncidentService(Settings(INCIDENT_FAILURE_THRESHOLD=1, _env_file=None))
    service.incidents = repository
    service.checks = ThresholdHealthCheckRepository()
    return service


def test_normal_incident_creation_result_is_explicitly_created() -> None:
    db = FakeSavepointSession()

    result = IncidentRepository().create_in_transaction(
        db,
        {
            "service_id": 1,
            "status": IncidentStatus.OPEN,
            "started_at": CHECKED_AT,
            "reason": "Serviço offline",
        },
    )

    assert isinstance(result, IncidentCreationResult)
    assert result.created is True
    assert result.incident in db.pending


def test_expected_uniqueness_race_result_is_explicitly_not_created() -> None:
    competing = Incident(
        id=42,
        service_id=1,
        status=IncidentStatus.OPEN,
        reason="Serviço offline",
    )
    db = FakeSavepointSession(make_integrity_error("uq_incidents_service_id_open"))

    result = CompetingIncidentRepository(competing).create_in_transaction(
        db,
        {
            "service_id": 1,
            "status": IncidentStatus.OPEN,
            "started_at": CHECKED_AT,
            "reason": "Serviço offline",
        },
    )

    assert result == IncidentCreationResult(incident=competing, created=False)


def test_losing_worker_commits_health_check_without_transition_or_notification() -> None:
    error = make_integrity_error("uq_incidents_service_id_open")
    db = FakeSavepointSession(error)
    competing = Incident(
        id=42,
        service_id=1,
        status=IncidentStatus.OPEN,
        reason="Serviço offline",
    )
    notifications = FakeNotificationService()

    _check, transition = run_workflow(
        db,
        FakeCheckRepository(),
        make_incident_service(SequentialRaceIncidentRepository(competing)),
        notifications,
    )

    assert db.persisted == ["check"]
    assert db.begin_nested_calls == 1
    assert db.savepoint_rollback_calls == 1
    assert db.commit_calls == 1
    assert db.rollback_calls == 0
    assert transition is None
    assert notifications.calls == []


def test_simulated_winner_and_loser_produce_exactly_one_notification() -> None:
    notifications = FakeNotificationService()
    winner_db = FakeSavepointSession()

    _winner_check, winner_transition = run_workflow(
        winner_db,
        FakeCheckRepository(),
        make_incident_service(NoOpenIncidentRepository()),
        notifications,
    )
    assert winner_transition is not None
    loser_db = FakeSavepointSession(make_integrity_error("uq_incidents_service_id_open"))
    _loser_check, loser_transition = run_workflow(
        loser_db,
        FakeCheckRepository(),
        make_incident_service(SequentialRaceIncidentRepository(winner_transition.incident)),
        notifications,
    )

    assert winner_transition.event_type == NotificationEventType.INCIDENT_OPENED
    assert loser_transition is None
    assert winner_db.commit_calls == 1
    assert loser_db.persisted == ["check"]
    assert loser_db.commit_calls == 1
    assert len(notifications.calls) == 1


def test_unrelated_integrity_error_rolls_back_and_propagates() -> None:
    error = make_integrity_error("incidents_service_id_fkey")
    db = FakeSavepointSession(error)
    competing = Incident(
        id=42,
        service_id=1,
        status=IncidentStatus.OPEN,
        reason="Serviço offline",
    )
    notifications = FakeNotificationService()

    with pytest.raises(IntegrityError) as raised:
        run_workflow(
            db,
            FakeCheckRepository(),
            make_incident_service(SequentialRaceIncidentRepository(competing)),
            notifications,
        )

    assert raised.value is error
    assert db.persisted == []
    assert db.pending == []
    assert db.savepoint_rollback_calls == 1
    assert db.commit_calls == 0
    assert db.rollback_calls == 1
    assert notifications.calls == []
