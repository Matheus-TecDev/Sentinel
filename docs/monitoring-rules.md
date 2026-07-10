# Monitoring Rules

## Scheduling

`AsyncIOScheduler` runs `execute_healthchecks` at the interval configured by `HEALTHCHECK_INTERVAL_SECONDS`.

Job configuration:

- `max_instances=1`: prevents overlap within the same process;
- `coalesce=True`: consolidates delayed executions;
- first execution approximately five seconds after startup;
- UTC timezone.

Only active services are selected.

## Check Execution

For each service, the worker performs a GET request with:

- timeout defined by `HEALTHCHECK_TIMEOUT_SECONDS`;
- redirects enabled;
- total duration measured with a monotonic clock.

## Classification

| Condition | Result |
| --- | --- |
| HTTP 200–399 within the latency threshold | `online` |
| HTTP 200–399 above `DEGRADED_RESPONSE_TIME_MS` | `degraded` |
| HTTP outside 200–399 | `offline` |
| Timeout or HTTP/network error | `offline` |

Each result persists the HTTP status code, latency, error, and timestamp.

## Incidents

After each check:

- an `offline` or `degraded` result without an open incident creates one;
- subsequent problematic results update the open incident;
- an `online` result resolves the open incident and calculates its duration;
- an `online` result without an open incident causes no transition.

Under the synchronization rule, a service has at most one open incident relevant to the workflow.

## Notifications

Notifications are triggered only on these transitions:

- incident opened;
- service recovered and incident resolved.

Each channel selects whether it receives outage, degradation, and recovery events.

Implemented destinations:

- generic HTTP webhook;
- Discord webhook.

The email type exists in the model, but SMTP is not implemented. Every attempt creates a `NotificationLog` with `sent` or `failed` status.

## Operational Considerations

The embedded scheduler is suitable for a single-replica MVP. Horizontal scaling requires moving monitoring execution to a coordinated worker or queue-based system to prevent duplicate checks.
