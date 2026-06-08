# Sentinel

Sentinel é uma plataforma de observabilidade para monitorar serviços, APIs e aplicações internas em um ambiente próximo ao uso corporativo.

O MVP concentra os recursos essenciais para operação: cadastro de serviços monitorados, verificações HTTP automáticas, Dashboard operacional, histórico de verificações, autenticação JWT e controle básico de acesso por perfil. A arquitetura já está preparada para evoluir com Prometheus, Grafana, Loki e Promtail.

## Objetivo técnico

Construir uma base profissional para monitoramento de aplicações, cobrindo backend, DevOps, infraestrutura, cloud e observabilidade:

- Backend FastAPI com responsabilidades bem separadas.
- Persistência em PostgreSQL com SQLAlchemy e migrações Alembic.
- Worker interno para verificações periódicas de disponibilidade.
- Console administrativo em React com interface responsiva para operação.
- Topologia Docker Compose com Nginx como proxy de entrada e banco isolado.
- Caminho claro para integração com ferramentas de observabilidade em produção.

## Arquitetura

```text
Sentinel/
  backend/
    app/
      api/routes/        endpoints REST
      core/              configuração, segurança, enums, erros e logging
      db/                sessão SQLAlchemy e carga inicial
      models/            modelos ORM
      repositories/      acesso ao banco de dados
      schemas/           contratos Pydantic
      services/          regras de negócio
      workers/           agendador de verificações
    alembic/             migrações
  frontend/
    src/
      api/               cliente da API
      auth/              contexto de sessão JWT
      components/        layout, cards, badges e estados
      pages/             login, Dashboard, serviços e usuários
  infra/nginx/           configuração do proxy reverso
  docker-compose.yml
```

## Stack

Backend:

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic
- JWT
- RBAC
- APScheduler
- HTTPX

Frontend:

- React
- TypeScript
- Vite
- CSS moderno
- lucide-react icons

Infra:

- Docker
- Docker Compose
- Nginx
- Volume persistente para PostgreSQL

## Execução com Docker

```bash
cp .env.example .env
docker compose up -d --build
```

Acesse:

- Frontend: http://localhost
- Health do backend: http://localhost/health
- API via Nginx: http://localhost/api

O container do backend executa `alembic upgrade head` automaticamente antes de iniciar a API.

## Administrador inicial

Credenciais padrão de desenvolvimento em `.env.example`:

```text
Email: admin@sentinel.local
Password: ChangeMe123!
```

Altere `INITIAL_ADMIN_PASSWORD` e `JWT_SECRET_KEY` antes de usar o projeto fora do ambiente local.

## Desenvolvimento local

Backend:

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Ao executar fora do Docker, configure `DATABASE_URL` apontando para uma instância acessível do PostgreSQL.

## Variáveis de ambiente

| Variável | Finalidade |
| --- | --- |
| `POSTGRES_DB` | Nome do banco PostgreSQL |
| `POSTGRES_USER` | Usuário do PostgreSQL |
| `POSTGRES_PASSWORD` | Senha do PostgreSQL |
| `DATABASE_URL` | String de conexão SQLAlchemy do backend |
| `JWT_SECRET_KEY` | Segredo usado para assinar tokens JWT |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Tempo de expiração do token |
| `BACKEND_CORS_ORIGINS` | Origens permitidas para CORS, separadas por vírgula |
| `HEALTHCHECK_INTERVAL_SECONDS` | Intervalo entre execuções do monitoramento |
| `HEALTHCHECK_TIMEOUT_SECONDS` | Timeout HTTP por serviço |
| `DEGRADED_RESPONSE_TIME_MS` | Limite de tempo para considerar um serviço degradado |
| `ENABLE_HEALTHCHECK_WORKER` | Ativa ou desativa o agendador interno |
| `INITIAL_ADMIN_EMAIL` | Email do administrador inicial |
| `INITIAL_ADMIN_PASSWORD` | Senha do administrador inicial |
| `NGINX_PORT` | Porta exposta pelo Nginx no host |

## Principais endpoints

Auth:

- `POST /api/auth/login`
- `GET /api/auth/me`

Users:

- `GET /api/users`
- `POST /api/users`
- `PUT /api/users/{id}`
- `PATCH /api/users/{id}/activation`

Services:

- `GET /api/services`
- `POST /api/services`
- `GET /api/services/{id}`
- `PUT /api/services/{id}`
- `PATCH /api/services/{id}/activation`
- `GET /api/services/{id}/checks`
- `GET /api/services/checks/history`
- `GET /api/services/checks/failures`

Dashboard:

- `GET /api/dashboard`

Health:

- `GET /health`

## RBAC

- `ADMIN`: gerencia usuários e serviços, além de visualizar Dashboard e detalhes.
- `OPERATOR`: gerencia serviços e visualiza Dashboard e detalhes.
- `VIEWER`: visualiza Dashboard e detalhes dos serviços.

## Regras de verificação

O worker do backend verifica serviços ativos em um intervalo configurável:

- Status HTTP de `200` a `399`: `online`.
- Status HTTP fora dessa faixa ou falha de rede: `offline`.
- Resposta bem-sucedida acima de `DEGRADED_RESPONSE_TIME_MS`: `degraded`.
- Timeout controlado por `HEALTHCHECK_TIMEOUT_SECONDS`.

Cada verificação é persistida com id do serviço, status, código HTTP, tempo de resposta, mensagem de erro e data da execução.

## Comandos Docker

```bash
docker compose config
docker compose up -d --build
docker compose logs -f backend
docker compose ps
docker compose down
docker compose down -v
```

Use `docker compose down -v` somente quando quiser remover o volume do PostgreSQL e apagar os dados locais.

## MVP atual

Implementado:

- Login com JWT.
- Usuário administrador inicial.
- Dependências de RBAC nas rotas do backend.
- Cadastro e gestão de serviços monitorados.
- Ativação e desativação de serviços.
- Worker interno com verificações persistidas.
- Dashboard com totais, contagens online/offline/degradado, tempo médio de resposta, falhas recentes e uptime.
- Detalhes do serviço com últimas verificações e falhas recentes.
- Administração de usuários.
- Nginx como proxy reverso.
- Docker Compose com PostgreSQL persistente.

Limitações atuais:

- Ainda não há endpoint real de métricas.
- Ainda não há tracing distribuído.
- Ainda não há pipeline de agregação de logs.
- Ainda não há fluxo de redefinição de senha.
- Ainda não há trilha granular de auditoria.
- As verificações atuais são apenas HTTP.

## Roadmap

Fase 2 de observabilidade:

- Expor `/metrics` no backend usando Prometheus client.
- Adicionar Prometheus ao Docker Compose.
- Adicionar Grafana com datasource e dashboards provisionados.
- Adicionar Loki para armazenamento de logs.
- Adicionar Promtail para coletar logs dos containers.
- Adicionar cAdvisor para métricas de containers.
- Adicionar Node Exporter para métricas do host.
- Criar dashboards para latência da API, taxa de erro, duração do worker, distribuição de status das verificações e uptime dos serviços.
- Adicionar regras de alerta para serviços offline e tempo de resposta degradado.

Fase 3 de maturidade da plataforma:

- Adicionar refresh tokens.
- Adicionar logs de auditoria.
- Adicionar tags de serviço e grupos responsáveis.
- Adicionar integrações de notificação.
- Adicionar verificações sintéticas por região.
- Adicionar instrumentação com OpenTelemetry.
