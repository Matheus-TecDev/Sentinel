import logging
from collections.abc import Callable, Iterator

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Histogram
from prometheus_client.core import GaugeMetricFamily
from sqlalchemy.orm import Session

from app.core.enums import HealthStatus
from app.db.session import SessionLocal
from app.repositories.incident_repository import IncidentRepository

logger = logging.getLogger(__name__)


class HealthCheckMetrics:
    def __init__(self, registry: CollectorRegistry) -> None:
        self.total = Counter(
            "sentinel_health_checks",
            "Total outbound health checks performed by Sentinel.",
            labelnames=("service_id", "status"),
            registry=registry,
        )
        self.duration_seconds = Histogram(
            "sentinel_health_check_duration_seconds",
            "Duration of outbound health checks performed by Sentinel in seconds.",
            labelnames=("service_id",),
            registry=registry,
        )

    def record(self, service_id: int, status: HealthStatus, duration_seconds: float) -> None:
        service_id_label = str(service_id)
        self.total.labels(service_id=service_id_label, status=status.value).inc()
        self.duration_seconds.labels(service_id=service_id_label).observe(duration_seconds)


class OpenIncidentCollector:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        repository: IncidentRepository,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository

    def describe(self) -> Iterator[GaugeMetricFamily]:
        yield GaugeMetricFamily(
            "sentinel_open_incidents",
            "Current number of persisted open incidents.",
        )

    def collect(self) -> Iterator[GaugeMetricFamily]:
        db: Session | None = None
        try:
            db = self._session_factory()
            open_incidents = max(0, self._repository.count_open(db))
        except Exception:
            logger.error("Failed to collect sentinel_open_incidents")
            return
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    logger.error("Failed to close open incident metric database session")
        yield GaugeMetricFamily(
            "sentinel_open_incidents",
            "Current number of persisted open incidents.",
            value=open_incidents,
        )


def register_open_incident_collector(
    registry: CollectorRegistry,
    session_factory: Callable[[], Session],
    repository: IncidentRepository,
) -> OpenIncidentCollector:
    collector = OpenIncidentCollector(session_factory, repository)
    registry.register(collector)
    return collector


health_check_metrics = HealthCheckMetrics(REGISTRY)
open_incident_collector = register_open_incident_collector(
    REGISTRY,
    SessionLocal,
    IncidentRepository(),
)
