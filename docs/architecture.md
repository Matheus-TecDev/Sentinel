# Architecture

## Overview

Sentinela is organized as a containerized full-stack application. Nginx is the entry point, the React frontend provides the operational interface, and the FastAPI backend handles authentication, monitoring rules, incidents, and persistence.

```text
Client -> Nginx -> React frontend
                  -> FastAPI API -> PostgreSQL
                           |
                           +-> APScheduler -> HTTP checks
                                             |
                                             +-> incidents
                                             +-> notifications

Prometheus -> API + cAdvisor + Node Exporter
Grafana    -> Prometheus + Loki
Promtail   -> Loki
```

## Components

| Component | Responsibility |
| --- | --- |
| Nginx | Single entry point and reverse proxy |
| Frontend | Dashboard and monitored-service operations |
| FastAPI | API, authentication, RBAC, and business rules |
| PostgreSQL | Users, services, checks, incidents, channels, and notifications |
| APScheduler | Scheduled check execution |
| Prometheus | Collection of HTTP, host, and container metrics |
| Grafana | Metrics and logs querying and visualization |
| Loki and Promtail | Container log storage and collection |
| cAdvisor | Container metrics |
| Node Exporter | Host metrics |

## Backend Organization

```text
app/
  api/routes/     HTTP routes
  core/           Configuration, security, enums, errors, and logging
  db/             Database session and initialization
  models/         SQLAlchemy entities
  repositories/   Queries and persistence
  schemas/        Pydantic contracts
  services/       Business rules
  workers/        Check scheduler
```

Routes delegate business rules to services; services use repositories for database access. The worker calls the health-check service, synchronizes incidents, and triggers notifications.

## Initialization

During the API lifespan:

1. logging is configured;
2. the initial administrator is created when necessary;
3. the scheduler starts when `ENABLE_HEALTHCHECK_WORKER=true`;
4. the scheduler shuts down during application termination.

The backend container runs `alembic upgrade head` before starting Uvicorn.

## Persistence

Main entities:

- `User`: identity, role, and activation state;
- `MonitoredService`: URL, environment, owner, and activation state;
- `HealthCheckResult`: individual result of each check;
- `Incident`: period of outage or degradation;
- `AlertChannel`: notification destination and preferences;
- `NotificationLog`: result of each delivery attempt.

Checks, incidents, channels, and notification logs belong to a monitored service.

## Current Limitations

- The scheduler runs inside the API process. Multiple replicas may execute duplicate checks without external coordination.
- Active services are processed sequentially.
- Alerts are delivered within the worker flow without a persistent queue.
- SMTP is modeled, but email delivery is not implemented.
- The current environment targets Docker Compose; cloud infrastructure is not declared.
