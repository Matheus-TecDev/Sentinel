from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AlertChannelType, NotificationEventType, NotificationStatus
from app.db.base import Base


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    incident_id: Mapped[int | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    channel_type: Mapped[AlertChannelType] = mapped_column(
        SAEnum(
            AlertChannelType,
            values_callable=lambda enum: [member.value for member in enum],
            native_enum=False,
            length=20,
        ),
        nullable=False,
    )
    target: Mapped[str] = mapped_column(String(2048), nullable=False)
    event_type: Mapped[NotificationEventType] = mapped_column(
        SAEnum(
            NotificationEventType,
            values_callable=lambda enum: [member.value for member in enum],
            native_enum=False,
            length=40,
        ),
        index=True,
        nullable=False,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        SAEnum(
            NotificationStatus,
            values_callable=lambda enum: [member.value for member in enum],
            native_enum=False,
            length=20,
        ),
        index=True,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)

    service = relationship("MonitoredService", back_populates="notification_logs")
    incident = relationship("Incident", back_populates="notification_logs")
