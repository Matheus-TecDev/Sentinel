# Sentinela

Sentinela is a full-stack monitoring platform for APIs, internal services, and business applications, built with FastAPI, PostgreSQL, React, Docker, and an integrated observability stack.

The platform runs scheduled HTTP checks, maintains availability history, and provides an operational view of services that are online, degraded, or unavailable.

## Technology Stack

| Area | Technologies |
| --- | --- |
| Backend | Python, FastAPI, SQLAlchemy, Alembic, Pydantic, APScheduler, HTTPX |
| Frontend | React, TypeScript, Vite |
| Data | PostgreSQL |
| Security | JWT, RBAC |
| Observability | Prometheus, Grafana, Loki, Promtail, cAdvisor, Node Exporter |
| Infrastructure | Docker Compose, Nginx, GitHub Actions, GHCR |

## Problem

Technical teams need to detect outages and degradation before they affect users for extended periods. Sentinela centralizes monitored-service configuration, runs automated checks, and records operational data for investigation.

## Features

- Monitored-service registration and management.
- Automated HTTP checks at configurable intervals.
- Online, offline, and degraded service classification.
- Persistent check history.
- Automatic incident creation and resolution.
- Webhook and Discord notifications with delivery history.
- Operational dashboard.
- JWT authentication and role-based access control.
- HTTP metrics exposed to Prometheus.
- Provisioned Grafana dashboards.
- Centralized logs with Loki and Promtail.
- Host and container metrics with Node Exporter and cAdvisor.
- Nginx reverse proxy.
- Image build and publishing pipeline for GHCR.

## Architecture

```text
User -> Nginx -> React
                -> FastAPI -> PostgreSQL
                               |
Monitoring worker --------------+

Prometheus -> FastAPI + cAdvisor + Node Exporter
Grafana    -> Prometheus + Loki
Promtail   -> Loki
```

## Monitoring Rules

- HTTP responses from `200` through `399`: service is online.
- Network errors, timeouts, or responses outside that range: service is offline.
- Successful responses above the configured latency threshold: service is degraded.

Each check records the service, calculated status, HTTP status code, response time, error message, and execution timestamp.

## Access Roles

| Role | Permissions |
| --- | --- |
| `ADMIN` | Manages users and services and accesses all operational views |
| `OPERATOR` | Manages services and monitors operations |
| `VIEWER` | Views the dashboard, services, and history |

## Running Locally

```bash
cp .env.example .env
docker compose up -d --build
```

Main URLs:

- Application: http://localhost
- API: http://localhost/api
- Health check: http://localhost/health
- Metrics: http://localhost/metrics
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

The backend applies Alembic migrations during startup.

## Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/auth/login` | Authenticates a user |
| `GET` | `/api/auth/me` | Returns the authenticated user |
| `GET` | `/api/users` | Lists users |
| `POST` | `/api/users` | Creates a user |
| `PUT` | `/api/users/{id}` | Updates a user |
| `PATCH` | `/api/users/{id}/activation` | Activates or deactivates a user |
| `GET` | `/api/services` | Lists monitored services |
| `POST` | `/api/services` | Registers a service |
| `GET` | `/api/services/{id}` | Returns service details |
| `PUT` | `/api/services/{id}` | Updates a service |
| `PATCH` | `/api/services/{id}/activation` | Enables or disables monitoring |
| `GET` | `/api/services/{id}/checks` | Lists service checks |
| `GET` | `/api/dashboard` | Returns operational data |
| `GET` | `/health` | Checks API health |
| `GET` | `/metrics` | Exposes Prometheus metrics |

## Project Structure

```text
backend/   API, business rules, persistence, and monitoring worker
frontend/  React operational dashboard
infra/     Nginx, Prometheus, Grafana, Loki, and Promtail
.github/   Integration and publishing pipeline
```

## Documentation

| Document | Coverage |
| --- | --- |
| [Architecture](docs/architecture.md) | Components, persistence, initialization, and limitations |
| [API](docs/api.md) | Endpoints, access levels, and errors |
| [Authentication and RBAC](docs/authentication-and-rbac.md) | JWT, passwords, roles, and permissions |
| [Monitoring rules](docs/monitoring-rules.md) | Scheduler, checks, incidents, and notifications |
| [Observability](docs/observability.md) | Metrics, logs, health checks, and current gaps |

## Validation

```bash
cd backend
python -m compileall app
python -c "from app.main import app; print('Backend OK')"

cd ../frontend
npm ci
npm run build

cd ..
docker compose config
```

## Status

**MVP complete.**

The initial scope covers automated monitoring, incidents, webhook and Discord notifications, the operational dashboard, RBAC, metrics, logs, and containerized execution. Distributed tracing, SMTP delivery, and multi-replica coordination remain planned improvements.
