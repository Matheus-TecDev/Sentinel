import asyncio
from collections.abc import Callable, Iterator

import httpx
import pytest
from prometheus_client import CollectorRegistry, generate_latest

from app.core.config import Settings
from app.core.enums import HealthStatus, ServiceEnvironment
from app.models.service import MonitoredService
from app.observability.metrics import HealthCheckMetrics
from app.services.health_check_service import perform_health_check


class FakeHttpClient:
    def __init__(
        self,
        response: httpx.Response | None = None,
        error: httpx.HTTPError | None = None,
    ) -> None:
        self.response = response
        self.error = error

    async def get(self, _url: str) -> httpx.Response:
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def make_service() -> MonitoredService:
    return MonitoredService(
        id=42,
        name="Sensitive Payments Service",
        environment=ServiceEnvironment.PRODUCTION,
        healthcheck_url="https://private.example.com/health?token=secret",
        owner="Platform Team",
        is_active=True,
    )


def make_clock(*values: float) -> Callable[[], float]:
    readings: Iterator[float] = iter(values)
    return lambda: next(readings)


def run_check(
    client: FakeHttpClient,
    registry: CollectorRegistry,
    *,
    degraded_threshold_ms: int = 1000,
    clock_values: tuple[float, ...] = (10.0, 10.1, 10.2),
) -> dict:
    return asyncio.run(
        perform_health_check(
            make_service(),
            client,
            Settings(DEGRADED_RESPONSE_TIME_MS=degraded_threshold_ms, _env_file=None),
            metrics=HealthCheckMetrics(registry),
            clock=make_clock(*clock_values),
        )
    )


def test_successful_health_check_increments_online_counter() -> None:
    registry = CollectorRegistry()

    result = run_check(FakeHttpClient(response=httpx.Response(200)), registry)

    assert result["status"] == HealthStatus.ONLINE
    assert (
        registry.get_sample_value(
            "sentinel_health_checks_total",
            {"service_id": "42", "status": "online"},
        )
        == 1
    )


def test_network_failure_increments_offline_counter() -> None:
    registry = CollectorRegistry()
    request = httpx.Request("GET", "https://private.example.com/health?token=secret")
    error = httpx.ConnectError("connection refused with private details", request=request)

    result = run_check(
        FakeHttpClient(error=error),
        registry,
        clock_values=(10.0, 10.2),
    )

    assert result["status"] == HealthStatus.OFFLINE
    assert (
        registry.get_sample_value(
            "sentinel_health_checks_total",
            {"service_id": "42", "status": "offline"},
        )
        == 1
    )


def test_slow_health_check_increments_degraded_counter() -> None:
    registry = CollectorRegistry()

    result = run_check(
        FakeHttpClient(response=httpx.Response(200)),
        registry,
        degraded_threshold_ms=100,
        clock_values=(10.0, 10.2, 10.25),
    )

    assert result["status"] == HealthStatus.DEGRADED
    assert (
        registry.get_sample_value(
            "sentinel_health_checks_total",
            {"service_id": "42", "status": "degraded"},
        )
        == 1
    )


def test_health_check_duration_histogram_observes_seconds() -> None:
    registry = CollectorRegistry()

    run_check(
        FakeHttpClient(response=httpx.Response(200)),
        registry,
        clock_values=(10.0, 10.1, 10.25),
    )

    labels = {"service_id": "42"}
    assert registry.get_sample_value("sentinel_health_check_duration_seconds_count", labels) == 1
    assert registry.get_sample_value("sentinel_health_check_duration_seconds_sum", labels) == pytest.approx(0.25)


def test_metric_labels_exclude_sensitive_service_and_error_details() -> None:
    registry = CollectorRegistry()
    request = httpx.Request("GET", "https://private.example.com/health?token=secret")
    error = httpx.ConnectError("connection refused with private details", request=request)

    run_check(FakeHttpClient(error=error), registry, clock_values=(10.0, 10.2))

    metric_output = generate_latest(registry).decode()
    label_names = {
        label_name for metric in registry.collect() for sample in metric.samples for label_name in sample.labels
    }
    assert label_names - {"le"} == {"service_id", "status"}
    assert "private.example.com" not in metric_output
    assert "Sensitive Payments Service" not in metric_output
    assert "connection refused with private details" not in metric_output
