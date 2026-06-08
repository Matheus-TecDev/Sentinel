from sqlalchemy import Select, and_, desc, func, select
from sqlalchemy.orm import Session

from app.core.enums import HealthStatus
from app.models.health_check import HealthCheckResult


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

    def recent_for_service(self, db: Session, service_id: int, limit: int = 50) -> list[HealthCheckResult]:
        statement = (
            select(HealthCheckResult)
            .where(HealthCheckResult.service_id == service_id)
            .order_by(desc(HealthCheckResult.checked_at))
            .limit(limit)
        )
        return list(db.execute(statement).scalars().all())

    def history(self, db: Session, limit: int = 100) -> list[HealthCheckResult]:
        statement = select(HealthCheckResult).order_by(desc(HealthCheckResult.checked_at)).limit(limit)
        return list(db.execute(statement).scalars().all())

    def recent_failures(
        self,
        db: Session,
        service_id: int | None = None,
        limit: int = 10,
    ) -> list[HealthCheckResult]:
        statement: Select = select(HealthCheckResult).where(HealthCheckResult.status == HealthStatus.OFFLINE)
        if service_id is not None:
            statement = statement.where(HealthCheckResult.service_id == service_id)
        statement = statement.order_by(desc(HealthCheckResult.checked_at)).limit(limit)
        return list(db.execute(statement).scalars().all())

    def average_response_time(self, db: Session, service_id: int | None = None) -> float | None:
        statement = select(func.avg(HealthCheckResult.response_time_ms)).where(
            HealthCheckResult.response_time_ms.is_not(None)
        )
        if service_id is not None:
            statement = statement.where(HealthCheckResult.service_id == service_id)
        value = db.execute(statement).scalar_one_or_none()
        return round(float(value), 2) if value is not None else None

    def uptime_percent(self, db: Session, service_id: int | None = None) -> float:
        total_statement = select(func.count(HealthCheckResult.id))
        success_statement = select(func.count(HealthCheckResult.id)).where(
            HealthCheckResult.status.in_([HealthStatus.ONLINE, HealthStatus.DEGRADED])
        )
        if service_id is not None:
            total_statement = total_statement.where(HealthCheckResult.service_id == service_id)
            success_statement = success_statement.where(HealthCheckResult.service_id == service_id)
        total = db.execute(total_statement).scalar_one()
        if total == 0:
            return 0.0
        success = db.execute(success_statement).scalar_one()
        return round((success / total) * 100, 2)
