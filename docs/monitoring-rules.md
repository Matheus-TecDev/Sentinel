# Monitoring Rules

## Scheduling

The backend creates an `AsyncIOScheduler` in UTC when `ENABLE_HEALTHCHECK_WORKER=true`. It schedules `execute_healthchecks` with:

- interval: `HEALTHCHECK_INTERVAL_SECONDS`, default `60`;
- first execution: approximately five seconds after startup;
- `max_instances=1`, preventing overlap in the same backend process;
- `coalesce=True`, consolidating delayed runs.

Only active monitored services are selected. Services are checked sequentially.

## Check execution and classification

HTTPX performs a `GET` with redirects enabled and the timeout configured by `HEALTHCHECK_TIMEOUT_SECONDS`. A monotonic clock measures the complete execution.

| Condition | Persisted result |
| --- | --- |
| HTTP 200–399 at or below `DEGRADED_RESPONSE_TIME_MS` | `online` |
| HTTP 200–399 above `DEGRADED_RESPONSE_TIME_MS` | `degraded` |
| HTTP outside 200–399 | `offline` |
| Timeout or HTTP/network exception | `offline` |

Each result stores `service_id`, status, optional HTTP status, optional response time, optional error message, and a UTC check timestamp. Failed network requests therefore become persisted `offline` results rather than disappearing from the monitoring history.

The outbound metrics counter and duration histogram are recorded only after classification produces a result. Metric labels contain only bounded `service_id` and status values; URLs, service names, errors, and exception text are not metric labels.

## Incident lifecycle

`offline` and `degraded` are unhealthy for incident threshold purposes. The global backend setting `INCIDENT_FAILURE_THRESHOLD` is configurable through the Compose environment and defaults to three.

- Before the threshold, an unhealthy result persists without opening an incident.
- At the threshold, Sentinel opens an incident if none exists.
- Further unhealthy checks update `last_error_message` only when a concrete new error exists; the original opening reason is immutable.
- `online` resets the consecutive unhealthy sequence naturally and resolves an open incident.
- Resolution stores `status=resolved`, `resolved_at`, and a non-negative `duration_seconds`.
- Disabling an active monitored service also resolves its open incident.
- An online check or deactivation without an open incident causes no incident transition.

PostgreSQL enforces one open incident per service with the partial unique index `uq_incidents_service_id_open`. The health-check workflow handles only that named uniqueness race through a savepoint. The winner opens the incident; the loser reuses it without emitting a second incident-opened transition and still commits its own check.

## Transaction and notification ordering

For scheduled checks:

```text
outbound HTTP request
→ begin persistence work
→ flush health-check result
→ synchronize incident
→ one outer commit
→ deliver transition notifications
```

Check and incident persistence roll back together if either operation fails. Notifications are never attempted for a failed transaction.

For monitoring deactivation, service state is committed, the open incident is resolved and committed, and then the existing recovery notification contract runs. Notification delivery failure does not roll back the already persisted deactivation or resolution.

## Notifications

Sentinel emits only:

- `incident_opened`, and only for the transaction that actually created the incident;
- `incident_resolved`, after healthy recovery or monitoring deactivation.

Channels independently opt into offline, degraded, and recovery notifications. Implemented delivery types are generic HTTP webhooks and Discord webhooks. The email type is modeled, but an attempt is recorded as failed because SMTP is not implemented.

Every attempted delivery creates a `NotificationLog` with `sent` or `failed` status. Delivery happens after the state transition commits. Targets are masked in warning logs, although notification records retain their configured target as application data.

## Operational limitations

- The threshold is global rather than service-specific.
- `max_instances=1` protects only one backend process; it is not distributed coordination.
- Checks are sequential and may take longer as the service set grows.
- Notifications are direct post-commit calls without a queue, outbox, or durable retry worker.
