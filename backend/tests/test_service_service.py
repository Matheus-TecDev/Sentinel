import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.core.enums import IncidentStatus, NotificationEventType, ServiceEnvironment
from app.models.incident import Incident
from app.models.service import MonitoredService
from app.schemas.service import ServiceUpdate
from app.services.incident_service import IncidentService
from app.services.service_service import ServiceService


class FakeServiceRepository:
    def __init__(self, service: MonitoredService) -> None:
        self.service = service

    def get(self, _db: object, service_id: int) -> MonitoredService | None:
        return self.service if self.service.id == service_id else None

    def update(self, db: "FakeSession", service: MonitoredService, data: dict) -> MonitoredService:
        for key, value in data.items():
            setattr(service, key, value)
        db.events.append("service_commit")
        return service


class FakeHealthCheckRepository:
    def latest_by_service(self, _db: object) -> dict:
        return {}


class FakeIncidentRepository:
    def __init__(self, incident: Incident | None = None) -> None:
        self.incident = incident
        self.update_calls = 0

    def open_for_service(self, _db: object, service_id: int) -> Incident | None:
        if (
            self.incident is not None
            and self.incident.service_id == service_id
            and self.incident.status == IncidentStatus.OPEN
        ):
            return self.incident
        return None

    def update(self, db: "FakeSession", incident: Incident, data: dict) -> Incident:
        self.update_calls += 1
        for key, value in data.items():
            setattr(incident, key, value)
        db.events.append("incident_commit")
        return incident


class FakeSession:
    def __init__(self) -> None:
        self.events: list[str] = []


class FakeNotificationService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[Incident, NotificationEventType]] = []

    async def notify_incident_event(
        self,
        db: FakeSession,
        incident: Incident,
        event_type: NotificationEventType,
    ) -> list:
        db.events.append("notification")
        self.calls.append((incident, event_type))
        if self.error is not None:
            raise self.error
        return []


def make_service(is_active: bool = True) -> MonitoredService:
    timestamp = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)
    return MonitoredService(
        id=1,
        name="Payments API",
        environment=ServiceEnvironment.PRODUCTION,
        healthcheck_url="https://example.com/health",
        owner="Platform Team",
        is_active=is_active,
        created_at=timestamp,
        updated_at=timestamp,
    )


def make_open_incident() -> Incident:
    return Incident(
        id=1,
        service_id=1,
        status=IncidentStatus.OPEN,
        started_at=datetime(2026, 7, 12, 11, 0, tzinfo=timezone.utc),
        reason="Serviço offline",
        last_error_message="Connection refused",
    )


def make_service_service(
    service: MonitoredService,
    incident: Incident | None,
    resolved_at: datetime,
    notification_error: Exception | None = None,
) -> tuple[ServiceService, FakeIncidentRepository, FakeNotificationService]:
    service_service = ServiceService(clock=lambda: resolved_at)
    service_service.services = FakeServiceRepository(service)
    service_service.checks = FakeHealthCheckRepository()
    incident_repository = FakeIncidentRepository(incident)
    incident_service = IncidentService()
    incident_service.incidents = incident_repository
    service_service.incidents = incident_service
    notification_service = FakeNotificationService(notification_error)
    service_service.notifications = notification_service
    return service_service, incident_repository, notification_service


def test_disabling_active_service_resolves_open_incident() -> None:
    service = make_service()
    incident = make_open_incident()
    resolved_at = incident.started_at + timedelta(minutes=4, seconds=30)
    service_service, incident_repository, notifications = make_service_service(
        service, incident, resolved_at
    )
    db = FakeSession()

    result = asyncio.run(
        service_service.update(db, service.id, ServiceUpdate(is_active=False))
    )

    assert result.is_active is False
    assert incident.status == IncidentStatus.RESOLVED
    assert incident.resolved_at == resolved_at
    assert incident.duration_seconds == 270
    assert incident.reason == "Serviço offline"
    assert incident.last_error_message == "Connection refused"
    assert incident_repository.update_calls == 1
    assert notifications.calls == [(incident, NotificationEventType.INCIDENT_RESOLVED)]
    assert db.events == ["service_commit", "incident_commit", "notification"]


def test_disabling_service_without_open_incident_does_not_create_one() -> None:
    service = make_service()
    resolved_at = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    service_service, incident_repository, notifications = make_service_service(
        service, None, resolved_at
    )

    result = asyncio.run(service_service.set_active(FakeSession(), service.id, False))

    assert result.is_active is False
    assert incident_repository.incident is None
    assert incident_repository.update_calls == 0
    assert notifications.calls == []


def test_updating_already_inactive_service_does_not_resolve_incident() -> None:
    service = make_service(is_active=False)
    incident = make_open_incident()
    resolved_at = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    service_service, incident_repository, notifications = make_service_service(
        service, incident, resolved_at
    )

    result = asyncio.run(service_service.set_active(FakeSession(), service.id, False))

    assert result.is_active is False
    assert incident.status == IncidentStatus.OPEN
    assert incident_repository.update_calls == 0
    assert notifications.calls == []


def test_updating_unrelated_service_field_does_not_affect_incident() -> None:
    service = make_service()
    incident = make_open_incident()
    resolved_at = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    service_service, incident_repository, notifications = make_service_service(
        service, incident, resolved_at
    )

    result = asyncio.run(
        service_service.update(
            FakeSession(), service.id, ServiceUpdate(name="Payments Gateway")
        )
    )

    assert result.name == "Payments Gateway"
    assert result.is_active is True
    assert incident.status == IncidentStatus.OPEN
    assert incident_repository.update_calls == 0
    assert notifications.calls == []


def test_reenabling_service_does_not_affect_incident() -> None:
    service = make_service(is_active=False)
    incident = make_open_incident()
    resolved_at = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    service_service, incident_repository, notifications = make_service_service(
        service, incident, resolved_at
    )

    result = asyncio.run(service_service.set_active(FakeSession(), service.id, True))

    assert result.is_active is True
    assert incident.status == IncidentStatus.OPEN
    assert incident_repository.update_calls == 0
    assert notifications.calls == []


def test_activation_endpoint_path_sends_recovery_after_resolution() -> None:
    service = make_service()
    incident = make_open_incident()
    resolved_at = incident.started_at + timedelta(minutes=5)
    service_service, _incident_repository, notifications = make_service_service(
        service, incident, resolved_at
    )
    db = FakeSession()

    result = asyncio.run(service_service.set_active(db, service.id, False))

    assert result.is_active is False
    assert incident.status == IncidentStatus.RESOLVED
    assert notifications.calls == [(incident, NotificationEventType.INCIDENT_RESOLVED)]
    assert db.events == ["service_commit", "incident_commit", "notification"]


def test_notification_failure_does_not_undo_deactivation_or_resolution() -> None:
    service = make_service()
    incident = make_open_incident()
    resolved_at = incident.started_at + timedelta(minutes=5)
    service_service, _incident_repository, notifications = make_service_service(
        service,
        incident,
        resolved_at,
        notification_error=RuntimeError("notification failed"),
    )
    db = FakeSession()

    with pytest.raises(RuntimeError, match="notification failed"):
        asyncio.run(service_service.set_active(db, service.id, False))

    assert service.is_active is False
    assert incident.status == IncidentStatus.RESOLVED
    assert incident.resolved_at == resolved_at
    assert incident.reason == "Serviço offline"
    assert incident.last_error_message == "Connection refused"
    assert notifications.calls == [(incident, NotificationEventType.INCIDENT_RESOLVED)]
    assert db.events == ["service_commit", "incident_commit", "notification"]
