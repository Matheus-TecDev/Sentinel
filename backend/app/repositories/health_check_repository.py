from datetime import datetime

from sqlalchemy import Select, and_, case, desc, func, select
from sqlalchemy.orm import Session

from app.core.enums import HealthStatus
from app.models.health_check import HealthCheckResult
from app.models.service import MonitoredService


class HealthCheckRepository:
    def create(self, db: Session, data: dict) -> HealthCheckResult:
        result = HealthCheckResult(**data)
        db.add(result)
        db.commit()
        db.refresh(result)
        return result

    def latest_by_service(self, db: Session) -> dict[int, HealthCheckResult]:
        latest_subquery = (
            select(
                HealthCheckResult.service_id,
                func.max(HealthCheckResult.checked_at).label("checked_at"),
            )
            .group_by(HealthCheckResult.service_id)
            .subquery()
        )
        statement = (
            select(HealthCheckResult)
            .join(
                latest_subquery,
                and_(
                    HealthCheckResult.service_id == latest_subquery.c.service_id,
                    HealthCheckResult.checked_at == latest_subquery.c.checked_at,
                ),
            )
            .order_by(desc(HealthCheckResult.checked_at))
        )
        return {item.service_id: item for item in db.execute(statement).scalars().all()}

    def recent_for_service(
        self,
        db: Session,
        service_id: int,
        limit: int = 50,
        since: datetime | None = None,
    ) -> list[HealthCheckResult]:
        statement = (
            select(HealthCheckResult)
            .where(HealthCheckResult.service_id == service_id)
            .order_by(desc(HealthCheckResult.checked_at))
            .limit(limit)
        )
        if since is not None:
            statement = statement.where(HealthCheckResult.checked_at >= since)
        return list(db.execute(statement).scalars().all())

    def consecutive_unhealthy_count(self, db: Session, service_id: int, limit: int) -> int:
        statement = (
            select(HealthCheckResult.status)
            .where(HealthCheckResult.service_id == service_id)
            .order_by(desc(HealthCheckResult.checked_at), desc(HealthCheckResult.id))
            .limit(limit)
        )
        statuses = db.execute(statement).scalars().all()
        count = 0
        for status in statuses:
            if status == HealthStatus.ONLINE:
                break
            count += 1
        return count

    def history(self, db: Session, limit: int = 100) -> list[HealthCheckResult]:
        statement = select(HealthCheckResult).order_by(desc(HealthCheckResult.checked_at)).limit(limit)
        return list(db.execute(statement).scalars().all())

    def recent_failures(
        self,
        db: Session,
        service_id: int | None = None,
        limit: int = 10,
        since: datetime | None = None,
    ) -> list[HealthCheckResult]:
        statement: Select = select(HealthCheckResult).where(HealthCheckResult.status == HealthStatus.OFFLINE)
        if service_id is not None:
            statement = statement.where(HealthCheckResult.service_id == service_id)
        if since is not None:
            statement = statement.where(HealthCheckResult.checked_at >= since)
        statement = statement.order_by(desc(HealthCheckResult.checked_at)).limit(limit)
        return list(db.execute(statement).scalars().all())

    def average_response_time(
        self,
        db: Session,
        service_id: int | None = None,
        since: datetime | None = None,
    ) -> float | None:
        statement = select(func.avg(HealthCheckResult.response_time_ms)).where(
            HealthCheckResult.response_time_ms.is_not(None)
        )
        if service_id is not None:
            statement = statement.where(HealthCheckResult.service_id == service_id)
        if since is not None:
            statement = statement.where(HealthCheckResult.checked_at >= since)
        value = db.execute(statement).scalar_one_or_none()
        return round(float(value), 2) if value is not None else None

    def uptime_percent(
        self,
        db: Session,
        service_id: int | None = None,
        since: datetime | None = None,
    ) -> float:
        total_statement = select(func.count(HealthCheckResult.id))
        success_statement = select(func.count(HealthCheckResult.id)).where(
            HealthCheckResult.status.in_([HealthStatus.ONLINE, HealthStatus.DEGRADED])
        )
        if service_id is not None:
            total_statement = total_statement.where(HealthCheckResult.service_id == service_id)
            success_statement = success_statement.where(HealthCheckResult.service_id == service_id)
        if since is not None:
            total_statement = total_statement.where(HealthCheckResult.checked_at >= since)
            success_statement = success_statement.where(HealthCheckResult.checked_at >= since)
        total = db.execute(total_statement).scalar_one()
        if total == 0:
            return 0.0
        success = db.execute(success_statement).scalar_one()
        return round((success / total) * 100, 2)

    def availability_counts_between(
        self,
        db: Session,
        since: datetime,
        until: datetime,
    ) -> list[tuple[int, int, int]]:
        available_count = func.sum(
            case((HealthCheckResult.status == HealthStatus.ONLINE, 1), else_=0)
        )
        total_count = func.count(HealthCheckResult.id)
        statement = (
            select(
                MonitoredService.id,
                available_count.label("available_count"),
                total_count.label("total_count"),
            )
            .join(
                HealthCheckResult,
                HealthCheckResult.service_id == MonitoredService.id,
            )
            .where(
                HealthCheckResult.checked_at >= since,
                HealthCheckResult.checked_at <= until,
            )
            .group_by(MonitoredService.id)
        )
        return [
            (service_id, int(available), int(total))
            for service_id, available, total in db.execute(statement).all()
        ]

    def response_extremes(
        self,
        db: Session,
        service_id: int,
        since: datetime,
    ) -> tuple[float | None, float | None]:
        statement = select(
            func.max(HealthCheckResult.response_time_ms),
            func.min(HealthCheckResult.response_time_ms),
        ).where(
            HealthCheckResult.service_id == service_id,
            HealthCheckResult.checked_at >= since,
            HealthCheckResult.response_time_ms.is_not(None),
        )
        max_value, min_value = db.execute(statement).one()
        return (
            round(float(max_value), 2) if max_value is not None else None,
            round(float(min_value), 2) if min_value is not None else None,
        )

    def total_for_service(self, db: Session, service_id: int, since: datetime) -> int:
        statement = select(func.count(HealthCheckResult.id)).where(
            HealthCheckResult.service_id == service_id,
            HealthCheckResult.checked_at >= since,
        )
        return int(db.execute(statement).scalar_one())

    def failure_count(self, db: Session, service_id: int | None = None, since: datetime | None = None) -> int:
        statement = select(func.count(HealthCheckResult.id)).where(HealthCheckResult.status == HealthStatus.OFFLINE)
        if service_id is not None:
            statement = statement.where(HealthCheckResult.service_id == service_id)
        if since is not None:
            statement = statement.where(HealthCheckResult.checked_at >= since)
        return int(db.execute(statement).scalar_one())

    def latest_for_service(self, db: Session, service_id: int, since: datetime | None = None) -> HealthCheckResult | None:
        statement = (
            select(HealthCheckResult)
            .where(HealthCheckResult.service_id == service_id)
            .order_by(desc(HealthCheckResult.checked_at))
            .limit(1)
        )
        if since is not None:
            statement = statement.where(HealthCheckResult.checked_at >= since)
        return db.execute(statement).scalars().first()

    def status_counts_for_service(self, db: Session, service_id: int, since: datetime) -> dict[HealthStatus, int]:
        statement = (
            select(HealthCheckResult.status, func.count(HealthCheckResult.id))
            .where(HealthCheckResult.service_id == service_id, HealthCheckResult.checked_at >= since)
            .group_by(HealthCheckResult.status)
        )
        return {status: int(count) for status, count in db.execute(statement).all()}

    def unstable_services_since(self, db: Session, since: datetime, limit: int = 5) -> list[tuple[int, str, int, int]]:
        unhealthy_count = func.sum(
            case((HealthCheckResult.status.in_([HealthStatus.OFFLINE, HealthStatus.DEGRADED]), 1), else_=0)
        )
        failure_count = func.sum(case((HealthCheckResult.status == HealthStatus.OFFLINE, 1), else_=0))
        statement = (
            select(
                HealthCheckResult.service_id,
                MonitoredService.name,
                unhealthy_count.label("unhealthy_count"),
                failure_count.label("failure_count"),
            )
            .join(MonitoredService, MonitoredService.id == HealthCheckResult.service_id)
            .where(HealthCheckResult.checked_at >= since)
            .group_by(HealthCheckResult.service_id, MonitoredService.name)
            .having(unhealthy_count > 0)
            .order_by(desc("unhealthy_count"), desc("failure_count"), MonitoredService.name.asc())
            .limit(limit)
        )
        return [
            (service_id, name, int(unhealthy or 0), int(failures or 0))
            for service_id, name, unhealthy, failures in db.execute(statement).all()
        ]

    def slowest_services_since(self, db: Session, since: datetime, limit: int = 5) -> list[tuple[int, str, float]]:
        avg_response = func.avg(HealthCheckResult.response_time_ms)
        statement = (
            select(HealthCheckResult.service_id, MonitoredService.name, avg_response.label("average_response_time_ms"))
            .join(MonitoredService, MonitoredService.id == HealthCheckResult.service_id)
            .where(HealthCheckResult.checked_at >= since, HealthCheckResult.response_time_ms.is_not(None))
            .group_by(HealthCheckResult.service_id, MonitoredService.name)
            .order_by(desc("average_response_time_ms"), MonitoredService.name.asc())
            .limit(limit)
        )
        return [(service_id, name, round(float(avg), 2)) for service_id, name, avg in db.execute(statement).all()]
