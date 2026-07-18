import logging
from datetime import datetime, timedelta, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.health_check import HealthCheckResult
from app.repositories.health_check_repository import HealthCheckRepository
from app.repositories.service_repository import ServiceRepository
from app.services.health_check_service import perform_health_check
from app.services.incident_service import IncidentService, IncidentTransition
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


async def persist_check_and_sync_incident(
    db: Session,
    result: dict,
    check_repository: HealthCheckRepository,
    incident_service: IncidentService,
    notification_service: NotificationService,
) -> tuple[HealthCheckResult, IncidentTransition | None]:
    try:
        check = check_repository.create(db, result)
        transition = incident_service.sync_from_check(db, check)
        db.commit()
    except Exception:
        db.rollback()
        raise

    if transition and transition.event_type:
        await notification_service.notify_incident_event(
            db,
            transition.incident,
            transition.event_type,
        )
    return check, transition


async def execute_healthchecks() -> None:
    settings = get_settings()
    service_repository = ServiceRepository()
    check_repository = HealthCheckRepository()
    incident_service = IncidentService()
    notification_service = NotificationService()

    with SessionLocal() as db:
        services = service_repository.list_active(db)

    if not services:
        logger.info("No active services to check")
        return

    timeout = httpx.Timeout(settings.HEALTHCHECK_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for service in services:
            result = await perform_health_check(service, client, settings)
            with SessionLocal() as db:
                await persist_check_and_sync_incident(
                    db,
                    result,
                    check_repository,
                    incident_service,
                    notification_service,
                )
            logger.info(
                "Healthcheck completed service_id=%s status=%s response_time_ms=%s",
                service.id,
                result["status"].value,
                result["response_time_ms"],
            )


def start_healthcheck_scheduler() -> None:
    global _scheduler
    settings = get_settings()
    if _scheduler and _scheduler.running:
        return
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        execute_healthchecks,
        trigger="interval",
        seconds=settings.HEALTHCHECK_INTERVAL_SECONDS,
        id="sentinel_healthchecks",
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=5),
    )
    _scheduler.start()
    logger.info("Healthcheck worker started interval_seconds=%s", settings.HEALTHCHECK_INTERVAL_SECONDS)


def stop_healthcheck_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Healthcheck worker stopped")
    _scheduler = None
