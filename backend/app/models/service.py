from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ServiceEnvironment
from app.db.base import Base


class MonitoredService(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[ServiceEnvironment] = mapped_column(
        SAEnum(
            ServiceEnvironment,
            values_callable=lambda enum: [member.value for member in enum],
            native_enum=False,
            length=20,
        ),
        index=True,
        nullable=False,
    )
    healthcheck_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    responsible_id: Mapped[int | None] = mapped_column(
        ForeignKey("responsibles.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    checks = relationship(
        "HealthCheckResult",
        back_populates="service",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    incidents = relationship(
        "Incident",
        back_populates="service",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    alert_channels = relationship(
        "AlertChannel",
        back_populates="service",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notification_logs = relationship(
        "NotificationLog",
        back_populates="service",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    responsible = relationship("Responsible", back_populates="services")
