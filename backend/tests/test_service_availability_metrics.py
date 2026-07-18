from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.enums import HealthStatus
from app.observability.metrics import (
    HealthCheckMetrics,
    register_open_incident_collector,
    register_service_availability_collector,
)
from app.repositories.health_check_repository import HealthCheckRepository

NOW = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)


@dataclass
class FakeCheck:
    service_id: int
    status: HealthStatus
    checked_at: datetime


class FakeSession:
    def __init__(self) -> None:
        self.closed = False
        self.executed_statements: list[object] = []

    def execute(self, statement: object):
        self.executed_statements.append(statement)
        return FakeQueryResult([])

    def close(self) -> None:
        self.closed = True


class FakeSessionFactory:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.sessions: list[FakeSession] = []

    def __call__(self) -> FakeSession:
        if self.error is not None:
            raise self.error
        session = FakeSession()
        self.sessions.append(session)
        return session


class FakeQueryResult:
    def __init__(self, rows: list[tuple[int, int, int]]) -> None:
        self.rows = rows

    def all(self) -> list[tuple[int, int, int]]:
        return self.rows


class FakeAvailabilityRepository:
    def __init__(
        self,
        service_ids: set[int],
        checks: list[FakeCheck] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.service_ids = service_ids
        self.checks = checks or []
        self.error = error
        self.query_count = 0
        self.last_since: datetime | None = None
        self.last_until: datetime | None = None

    def availability_counts_between(
        self,
        _db: FakeSession,
        since: datetime,
        until: datetime,
    ) -> list[tuple[int, int, int]]:
        self.query_count += 1
        self.last_since = since
        self.last_until = until
        if self.error is not None:
            raise self.error

        rows: list[tuple[int, int, int]] = []
        for service_id in sorted(self.service_ids):
            recent_checks = [
                check
                for check in self.checks
                if check.service_id == service_id
                and since <= check.checked_at <= until
            ]
            if not recent_checks:
                continue
            available = sum(
                check.status == HealthStatus.ONLINE for check in recent_checks
            )
            rows.append((service_id, available, len(recent_checks)))
        return rows


class FakeIncidentRepository:
    def count_open(self, _db: FakeSession) -> int:
        return 2


def check(
    service_id: int,
    status: HealthStatus,
    age: timedelta = timedelta(),
) -> FakeCheck:
    return FakeCheck(service_id, status, NOW - age)


def make_registry(
    repository: FakeAvailabilityRepository,
    session_factory: FakeSessionFactory | None = None,
) -> tuple[CollectorRegistry, FakeSessionFactory]:
    registry = CollectorRegistry()
    session_factory = session_factory or FakeSessionFactory()
    register_service_availability_collector(
        registry,
        session_factory,
        repository,
        clock=lambda: NOW,
    )
    return registry, session_factory


def availability_value(
    registry: CollectorRegistry,
    service_id: int,
) -> float | None:
    return registry.get_sample_value(
        "sentinel_service_availability_ratio",
        {"service_id": str(service_id)},
    )


def record_existing_metrics(registry: CollectorRegistry) -> None:
    health_check_metrics = HealthCheckMetrics(registry)
    open_incident_factory = FakeSessionFactory()
    register_open_incident_collector(
        registry,
        open_incident_factory,
        FakeIncidentRepository(),
    )
    app = FastAPI()
    Instrumentator(
        registry=registry,
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        excluded_handlers=["/metrics"],
    ).instrument(app)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    health_check_metrics.total.labels(service_id="42", status="online").inc()
    with TestClient(app) as client:
        client.get("/health")


def test_online_checks_expose_full_availability() -> None:
    repository = FakeAvailabilityRepository(
        {1},
        [check(1, HealthStatus.ONLINE), check(1, HealthStatus.ONLINE)],
    )
    registry, _ = make_registry(repository)

    assert availability_value(registry, 1) == 1.0


def test_mixed_statuses_expose_correct_ratio() -> None:
    repository = FakeAvailabilityRepository(
        {1},
        [
            check(1, HealthStatus.ONLINE),
            check(1, HealthStatus.OFFLINE),
            check(1, HealthStatus.DEGRADED),
        ],
    )
    registry, _ = make_registry(repository)

    assert availability_value(registry, 1) == pytest.approx(1 / 3)


def test_offline_and_degraded_checks_are_unavailable() -> None:
    repository = FakeAvailabilityRepository(
        {1},
        [check(1, HealthStatus.OFFLINE), check(1, HealthStatus.DEGRADED)],
    )
    registry, _ = make_registry(repository)

    assert availability_value(registry, 1) == 0.0


def test_checks_older_than_twenty_four_hours_are_excluded() -> None:
    repository = FakeAvailabilityRepository(
        {1},
        [
            check(1, HealthStatus.ONLINE, timedelta(hours=24, seconds=1)),
            check(1, HealthStatus.OFFLINE, timedelta(hours=1)),
            FakeCheck(1, HealthStatus.ONLINE, NOW + timedelta(seconds=1)),
        ],
    )
    registry, _ = make_registry(repository)

    assert availability_value(registry, 1) == 0.0
    assert repository.last_since == NOW - timedelta(hours=24)
    assert repository.last_until == NOW


def test_service_without_recent_checks_is_omitted() -> None:
    repository = FakeAvailabilityRepository(
        {1, 2},
        [check(1, HealthStatus.ONLINE)],
    )
    registry, _ = make_registry(repository)

    assert availability_value(registry, 1) == 1.0
    assert availability_value(registry, 2) is None


def test_multiple_services_expose_independent_service_id_labels() -> None:
    repository = FakeAvailabilityRepository(
        {1, 2},
        [
            check(1, HealthStatus.ONLINE),
            check(2, HealthStatus.ONLINE),
            check(2, HealthStatus.OFFLINE),
        ],
    )
    registry, _ = make_registry(repository)

    assert availability_value(registry, 1) == 1.0
    assert availability_value(registry, 2) == 0.5
    samples = [
        sample
        for metric in registry.collect()
        for sample in metric.samples
        if sample.name == "sentinel_service_availability_ratio"
    ]
    assert all(set(sample.labels) == {"service_id"} for sample in samples)


def test_later_scrape_reflects_changed_persisted_state() -> None:
    repository = FakeAvailabilityRepository(
        {1},
        [check(1, HealthStatus.ONLINE)],
    )
    registry, _ = make_registry(repository)

    assert availability_value(registry, 1) == 1.0

    repository.checks.append(check(1, HealthStatus.OFFLINE))

    assert availability_value(registry, 1) == 0.5
    assert repository.query_count == 2


def test_repository_failure_omits_availability_and_preserves_other_metrics(
    caplog: pytest.LogCaptureFixture,
) -> None:
    repository = FakeAvailabilityRepository(
        {1},
        error=RuntimeError("postgresql://admin:secret@database/sentinel"),
    )
    registry, session_factory = make_registry(repository)
    record_existing_metrics(registry)

    with caplog.at_level("WARNING"):
        metric_output = generate_latest(registry).decode()

    assert "sentinel_service_availability_ratio" not in metric_output
    assert "sentinel_health_checks_total" in metric_output
    assert "sentinel_open_incidents 2.0" in metric_output
    assert "http_requests_total" in metric_output
    assert session_factory.sessions[-1].closed is True
    assert "Failed to collect sentinel_service_availability_ratio" in caplog.text
    assert "admin:secret" not in caplog.text


def test_session_factory_failure_does_not_propagate() -> None:
    repository = FakeAvailabilityRepository({1})
    session_factory = FakeSessionFactory(
        error=RuntimeError("postgresql://admin:secret@database/sentinel")
    )
    registry, _ = make_registry(repository, session_factory)

    metric_output = generate_latest(registry).decode()

    assert "sentinel_service_availability_ratio" not in metric_output
    assert session_factory.sessions == []


def test_successful_collection_closes_database_session() -> None:
    repository = FakeAvailabilityRepository(
        {1},
        [check(1, HealthStatus.ONLINE)],
    )
    registry, session_factory = make_registry(repository)

    assert availability_value(registry, 1) == 1.0
    assert session_factory.sessions[-1].closed is True


def test_exposition_excludes_forbidden_labels_and_sensitive_values() -> None:
    repository = FakeAvailabilityRepository(
        {42},
        [check(42, HealthStatus.ONLINE)],
    )
    registry, _ = make_registry(repository)

    metric_output = generate_latest(registry).decode()

    assert 'sentinel_service_availability_ratio{service_id="42"} 1.0' in metric_output
    assert "service_name" not in metric_output
    assert "healthcheck_url" not in metric_output
    assert "environment" not in metric_output
    assert "error_message" not in metric_output
    assert "private.example.com" not in metric_output


def test_repository_uses_one_aggregate_query_for_all_services() -> None:
    repository = HealthCheckRepository()
    session = FakeSession()

    result = repository.availability_counts_between(
        session,
        NOW - timedelta(hours=24),
        NOW,
    )

    assert result == []
    assert len(session.executed_statements) == 1
    sql = str(session.executed_statements[0])
    assert "JOIN health_check_results" in sql
    assert "health_check_results.status" in sql
    assert "health_check_results.checked_at >=" in sql
    assert "health_check_results.checked_at <=" in sql
    assert "GROUP BY services.id" in sql
