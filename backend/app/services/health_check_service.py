import time
from collections.abc import Callable

import httpx

from app.core.config import Settings, get_settings
from app.core.enums import HealthStatus
from app.models.service import MonitoredService
from app.observability.metrics import HealthCheckMetrics, health_check_metrics


async def perform_health_check(
    service: MonitoredService,
    client: httpx.AsyncClient,
    settings: Settings | None = None,
    metrics: HealthCheckMetrics = health_check_metrics,
    clock: Callable[[], float] = time.perf_counter,
) -> dict:
    settings = settings or get_settings()
    started_at = clock()
    http_status_code: int | None = None
    response_time_ms: float | None = None
    error_message: str | None = None

    try:
        response = await client.get(service.healthcheck_url)
        http_status_code = response.status_code
        response_time_ms = round((clock() - started_at) * 1000, 2)
        if 200 <= response.status_code <= 399:
            status = (
                HealthStatus.DEGRADED if response_time_ms > settings.DEGRADED_RESPONSE_TIME_MS else HealthStatus.ONLINE
            )
        else:
            status = HealthStatus.OFFLINE
            error_message = f"Status HTTP inesperado: {response.status_code}"
    except httpx.TimeoutException as exc:
        status = HealthStatus.OFFLINE
        error_message = f"Timeout na verificação: {exc}"
    except httpx.HTTPError as exc:
        status = HealthStatus.OFFLINE
        error_message = str(exc)

    result = {
        "service_id": service.id,
        "status": status,
        "http_status_code": http_status_code,
        "response_time_ms": response_time_ms,
        "error_message": error_message,
    }
    metrics.record(service.id, status, clock() - started_at)
    return result
