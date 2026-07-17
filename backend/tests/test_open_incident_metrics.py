from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.enums import IncidentStatus
from app.observability.metrics import (
    HealthCheckMetrics,
    register_open_incident_collector,
)


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeSessionFactory:
    def __init__(self, error: Exception | None = None) -> None:
        self.sessions: list[FakeSession] = []
        self.error = error

    def __call__(self) -> FakeSession:
        if self.error is not None:
            raise self.error
        session = FakeSession()
        self.sessions.append(session)
        return session


class FakeIncidentRepository:
    def __init__(
        self,
        statuses: list[IncidentStatus] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.statuses = statuses or []
        self.error = error

    def count_open(self, _db: FakeSession) -> int:
        if self.error is not None:
            raise self.error
        return sum(status == IncidentStatus.OPEN for status in self.statuses)


def make_registry(
    repository: FakeIncidentRepository,
    session_factory: FakeSessionFactory | None = None,
) -> tuple[CollectorRegistry, FakeSessionFactory]:
    registry = CollectorRegistry()
    session_factory = session_factory or FakeSessionFactory()
    register_open_incident_collector(registry, session_factory, repository)
    return registry, session_factory


def collect_value(registry: CollectorRegistry) -> float | None:
    return registry.get_sample_value("sentinel_open_incidents")


def record_existing_metrics(registry: CollectorRegistry) -> None:
    health_check_metrics = HealthCheckMetrics(registry)
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


def test_zero_persisted_open_incidents_exposes_zero() -> None:
    registry, _ = make_registry(FakeIncidentRepository())

    assert collect_value(registry) == 0


def test_multiple_persisted_open_incidents_expose_total() -> None:
    repository = FakeIncidentRepository(
        [IncidentStatus.OPEN, IncidentStatus.OPEN, IncidentStatus.OPEN]
    )
    registry, _ = make_registry(repository)

    assert collect_value(registry) == 3


def test_resolved_incidents_are_excluded() -> None:
    repository = FakeIncidentRepository(
        [IncidentStatus.OPEN, IncidentStatus.RESOLVED, IncidentStatus.RESOLVED]
    )
    registry, _ = make_registry(repository)

    assert collect_value(registry) == 1


def test_collection_reflects_repository_state_changes() -> None:
    repository = FakeIncidentRepository()
    registry, _ = make_registry(repository)

    assert collect_value(registry) == 0

    repository.statuses.extend([IncidentStatus.OPEN, IncidentStatus.OPEN])

    assert collect_value(registry) == 2


def test_database_session_closes_after_successful_collection() -> None:
    registry, session_factory = make_registry(
        FakeIncidentRepository([IncidentStatus.OPEN])
    )

    assert collect_value(registry) == 1
    assert session_factory.sessions[-1].closed is True


def test_repository_failure_omits_metric_and_preserves_other_metrics(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session_factory = FakeSessionFactory()
    registry, _ = make_registry(
        FakeIncidentRepository(
            error=RuntimeError("postgresql://admin:secret@database/sentinel")
        ),
        session_factory,
    )
    record_existing_metrics(registry)

    with caplog.at_level("ERROR"):
        metric_output = generate_latest(registry).decode()

    assert "sentinel_open_incidents" not in metric_output
    assert "sentinel_health_checks_total" in metric_output
    assert "http_requests_total" in metric_output
    assert session_factory.sessions[-1].closed is True
    assert "Failed to collect sentinel_open_incidents" in caplog.text
    assert "admin:secret" not in caplog.text


def test_session_factory_failure_omits_metric_without_propagating(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session_factory = FakeSessionFactory(
        error=RuntimeError("postgresql://admin:secret@database/sentinel")
    )
    registry, _ = make_registry(FakeIncidentRepository(), session_factory)

    with caplog.at_level("ERROR"):
        metric_output = generate_latest(registry).decode()

    assert "sentinel_open_incidents" not in metric_output
    assert session_factory.sessions == []
    assert "Failed to collect sentinel_open_incidents" in caplog.text
    assert "admin:secret" not in caplog.text


def test_existing_health_check_and_api_metrics_remain_registered() -> None:
    registry, _ = make_registry(FakeIncidentRepository())
    record_existing_metrics(registry)

    metric_output = generate_latest(registry).decode()
    assert "sentinel_open_incidents 0.0" in metric_output
    assert (
        'sentinel_health_checks_total{service_id="42",status="online"} 1.0'
        in metric_output
    )
    assert "# TYPE sentinel_health_check_duration_seconds histogram" in metric_output
    assert (
        'http_requests_total{handler="/health",method="GET",status="200"} 1.0'
        in metric_output
    )
