from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.alert import AlertChannel


class AlertChannelRepository:
    def get(self, db: Session, alert_id: int) -> AlertChannel | None:
        return db.get(AlertChannel, alert_id)

    def list_for_service(self, db: Session, service_id: int) -> list[AlertChannel]:
        statement = (
            select(AlertChannel).where(AlertChannel.service_id == service_id).order_by(desc(AlertChannel.created_at))
        )
        return list(db.execute(statement).scalars().all())

    def active_for_service(self, db: Session, service_id: int) -> list[AlertChannel]:
        statement = (
            select(AlertChannel)
            .where(AlertChannel.service_id == service_id, AlertChannel.is_active.is_(True))
            .order_by(desc(AlertChannel.created_at))
        )
        return list(db.execute(statement).scalars().all())

    def create(self, db: Session, data: dict) -> AlertChannel:
        channel = AlertChannel(**data)
        db.add(channel)
        db.commit()
        db.refresh(channel)
        return channel

    def update(self, db: Session, channel: AlertChannel, data: dict) -> AlertChannel:
        for key, value in data.items():
            setattr(channel, key, value)
        db.add(channel)
        db.commit()
        db.refresh(channel)
        return channel
