# Sentinel

Sentinel is a self-hosted monitoring platform for HTTP services. It centralizes service registration, runs scheduled outbound checks, classifies operational state, keeps a persistent history, and opens or resolves incidents automatically.

The project is designed as a portfolio-sized, end-to-end system: a FastAPI application and embedded scheduler share PostgreSQL state, a React interface exposes operational workflows, and a provisioned observability stack provides metrics, logs, dashboards, and alerts.

## Features

- Registration, filtering, activation, and management of monitored services and their responsible contacts.
- Periodic HTTP checks with configurable interval, timeout, and degraded-latency threshold.
- `online`, `degraded`, and `offline` classification with persistent check history.
- Automatic incident opening after a configurable consecutive-failure threshold and automatic recovery.
- A PostgreSQL partial unique index enforcing at most one open incident per service.
- Webhook and Discord incident/recovery notifications with delivery history.
- JWT authentication and role-based authorization for `ADMIN`, `OPERATOR`, and `VIEWER`.
- Operational React dashboard, service history, incidents, users, and responsibles.
- API, domain, container, and host metrics in Prometheus.
- A provisioned Grafana dashboard (`sentinel-overview`, 38 panels), five Prometheus alerts, and Alertmanager routing.
- Centralized Docker logs in Loki through Promtail.
- Explicit CPU and memory limits for all 11 Compose services.

## Architecture

```mermaid
flowchart LR
    Browser --> Nginx
    Nginx --> Frontend[React frontend]
    Nginx --> API[FastAPI API]
    API --> PostgreSQL
    Scheduler[APScheduler in backend] --> Target[Monitored HTTP service]
    Target --> Scheduler
    Scheduler --> PostgreSQL
    Scheduler --> Notify[Webhook / Discord]
    Prometheus --> API
    Prometheus --> cAdvisor
    Prometheus --> NodeExporter[Node Exporter]
    Prometheus --> Alertmanager
    Promtail --> Loki
    Grafana --> Prometheus
    Grafana --> Loki
```

For each scheduled execution, the backend performs the external HTTP request before opening a database transaction. The resulting check and its incident transition are then persisted atomically. Notifications run only after a successful commit. Prometheus records the check result and duration, while database-backed collectors calculate open incidents and 24-hour service availability at scrape time.

See [Architecture](docs/architecture.md) for component responsibilities, transaction guarantees, concurrency handling, and design trade-offs.

## Technology stack

| Area | Technologies |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic, APScheduler, HTTPX |
| Frontend | React 18, TypeScript, Vite, Recharts, Nginx |
| Data | PostgreSQL 16 |
| Security | HS256 JWT, PBKDF2 password hashing, RBAC |
| Observability | Prometheus, Alertmanager, Grafana, Loki, Promtail, cAdvisor, Node Exporter |
| Infrastructure | Docker Compose, Nginx reverse proxy, named volumes |
| CI | GitHub Actions, pytest, PostgreSQL integration tests, frontend build, GHCR images |

## Run locally

### Prerequisites

- Git;
- Docker Engine with Docker Compose v2;
- enough capacity for the configured maximum of 7 CPUs and 2.875 GiB of container memory.

Python 3.12 and Node.js 20 are needed only when running tests or builds directly on the host.

### Start the environment

```bash
git clone https://github.com/Matheus-TecDev/Sentinel.git
cd Sentinel
cp .env.example .env
docker compose up --build -d
docker compose ps
```

The backend container applies all Alembic migrations before Uvicorn starts. The first startup also creates the configured initial administrator if it does not exist.

Development defaults from `.env.example`:

- application user: `admin@sentinel.local`;
- application password: `ChangeMe123!`;
- Grafana user/password: `admin` / `admin`.

These credentials and all default secrets are for local demonstration only. Change them before using Sentinel outside an isolated development environment.

### Local addresses

| Component | Address | Exposure |
| --- | --- | --- |
| Application | <http://localhost> | Public host port through Nginx |
| API | <http://localhost/api> | Through Nginx |
| API health | <http://localhost/health> | Through Nginx |
| Prometheus metrics | <http://localhost/metrics> | Through Nginx |
| Prometheus | <http://localhost:9090> | Public host port |
| Grafana | <http://localhost:3000> | Public host port |

PostgreSQL, Alertmanager, Loki, Promtail, cAdvisor, Node Exporter, backend, and frontend do not publish host ports in the Compose configuration.

Check the application and database:

```bash
curl --fail http://localhost/health
curl --fail --head http://localhost/
docker compose exec postgres pg_isready -U sentinel -d sentinel
```

Stop containers while preserving data:

```bash
docker compose down
```

Remove containers and the named data volumes:

```bash
docker compose down --volumes
```

The second command permanently removes local PostgreSQL, Prometheus, Alertmanager, Grafana, and Loki volume data.

## Tests and validation

Install backend test dependencies and run unit tests:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-test.txt
python -m pytest -m "not integration"
```

PostgreSQL integration tests require an isolated database through `TEST_DATABASE_URL`. They apply Alembic migrations to that database and skip when the variable is absent:

```bash
docker run --rm --detach \
  --name sentinel-test-postgres \
  --publish 127.0.0.1:55432:5432 \
  --env POSTGRES_DB=sentinel_test \
  --env POSTGRES_USER=sentinel_test \
  --env POSTGRES_PASSWORD=sentinel_test_password \
  postgres:16-alpine

until docker exec sentinel-test-postgres \
  pg_isready -U sentinel_test -d sentinel_test; do sleep 1; done

TEST_DATABASE_URL=postgresql+psycopg://sentinel_test:sentinel_test_password@localhost:55432/sentinel_test \
  python -m pytest -m integration

docker rm --force sentinel-test-postgres
```

The GitHub Actions backend job provisions this dedicated PostgreSQL database and executes both test groups. To build the frontend and validate Compose:

```bash
cd ../frontend
npm ci
npm run build

cd ..
docker compose config --quiet
```

At the documentation snapshot, the complete backend suite passes **73 tests**, the frontend production build succeeds, and the integrated stack has been validated with all 11 containers running with `restart_count=0` and `OOMKilled=false`. These are recorded validation results, not a guarantee for future changes.

## Observability

Sentinel exposes:

- standard FastAPI request metrics from `prometheus-fastapi-instrumentator`;
- total outbound checks and their result status;
- outbound health-check duration histograms;
- the current persisted number of open incidents;
- persisted 24-hour availability per service;
- container metrics from cAdvisor and host metrics from Node Exporter;
- Docker logs collected by Promtail and stored in Loki.

Prometheus evaluates exactly five provisioned rules for backend availability, low service availability, open incidents, missing incident metrics, and high health-check latency. Alertmanager currently receives those alerts through an internal default receiver; no external Alertmanager notification destination is configured.

Grafana provisions Prometheus and Loki datasources and the `sentinel-overview` dashboard. See [Observability](docs/observability.md) for metric semantics, exact rules, and incident investigation procedures.

## Security

- Passwords are stored using salted PBKDF2-HMAC-SHA256 hashes.
- JWTs expire and authenticated requests reload the current user, role, and activation state from PostgreSQL.
- RBAC separates read, operate, and administration permissions.
- Alert delivery logs mask destination targets; database-backed metric collectors log generic failures without exception or connection details.
- One internal Compose network carries service-to-service traffic, and most components are not exposed on host ports.
- credentials, JWT secret, CORS origins, and initial administrator settings are configurable through environment variables.
- Every Compose service has explicit CPU and memory limits.

This remains a demonstrative local environment: HTTP is not terminated with TLS, Prometheus and Grafana are published without an external access-control layer, and development defaults are intentionally public.

## Decisions and trade-offs

- **Embedded APScheduler:** keeps deployment simple and shares application code, but binds scheduling to the backend process and prevents safe multi-replica scheduling without additional coordination.
- **Consecutive-failure threshold:** reduces incidents caused by transient failures, at the cost of delayed incident opening. The backend setting is global and defaults to three.
- **Partial unique index:** PostgreSQL enforces one open incident per service while retaining unlimited resolved history. A savepoint recovers the expected concurrent insert race without losing the worker's health-check result.
- **24-hour availability:** the Prometheus gauge is recalculated from committed checks on each scrape; `online` is available, while `degraded` and `offline` are unavailable. Services without checks in the window emit no sample.
- **Docker Compose:** provides a reproducible single-node demonstration rather than production orchestration or high availability.
- **Per-service resource limits:** prevent unbounded host consumption and reflect observed local usage, but static limits still require adjustment for different workloads and machines.

## Known limitations

- No high-availability deployment or public production environment is included.
- The scheduler is coupled to one backend process and checks active services sequentially.
- The deployment is single-node and persists data in local Docker volumes.
- Notification delivery has no queue or transactional outbox; webhook and Discord delivery are post-commit, but delivery retries are not coordinated by a durable worker.
- Email is represented in the data model but SMTP delivery is not implemented.
- Alertmanager has no external receiver configured.
- Distributed tracing, token refresh/revocation, MFA, and application-managed TLS are not implemented.
- The validated frontend build reports a large JavaScript chunk and npm audit warnings; these do not fail the current build.

## Repository structure

```text
.
├── backend/                 FastAPI application, migrations, and tests
├── frontend/                React/Vite application and frontend Nginx image
├── infra/                   Reverse proxy and observability configuration
├── docs/                    Technical documentation
├── .github/workflows/       CI and image publishing workflow
├── docker-compose.yml       Complete 11-service local stack
└── .env.example             Local configuration template
```

## Documentation

| Document | Coverage |
| --- | --- |
| [Architecture](docs/architecture.md) | Components, processing flow, consistency, and trade-offs |
| [API](docs/api.md) | Endpoints, access levels, and errors |
| [Authentication and RBAC](docs/authentication-and-rbac.md) | JWT, passwords, roles, and permissions |
| [Monitoring rules](docs/monitoring-rules.md) | Scheduling, classification, incidents, and notifications |
| [Observability](docs/observability.md) | Metrics, alerts, dashboard, logs, and investigation procedures |

No screenshots are versioned in the repository. This documentation intentionally avoids placeholders or generated evidence.
