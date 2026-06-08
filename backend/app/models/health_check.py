from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import HealthStatus
from app.db.base import Base


class HealthCheckResult(Base):
    __tablename__ = "health_check_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[HealthStatus] = mapped_column(
        SAEnum(
            HealthStatus,
            values_callable=lambda enum: [member.value for member in enum],
            native_enum=False,
            length=20,
        ),
        index=True,
        nullable=False,
    )
    http_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    service = relationship("MonitoredService", back_populates="checks")
