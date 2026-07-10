# Sentinela

Sentinela é uma plataforma full stack para monitoramento de APIs, serviços internos e aplicações corporativas, construída com FastAPI, PostgreSQL, React, Docker e uma stack integrada de observabilidade.

O projeto executa verificações HTTP periódicas, mantém histórico de disponibilidade e oferece uma visão operacional de serviços online, degradados ou indisponíveis.

## Tecnologias

| Área | Tecnologias |
| --- | --- |
| Backend | Python, FastAPI, SQLAlchemy, Alembic, Pydantic, APScheduler, HTTPX |
| Frontend | React, TypeScript, Vite |
| Dados | PostgreSQL |
| Segurança | JWT, RBAC |
| Observabilidade | Prometheus, Grafana, Loki, Promtail, cAdvisor, Node Exporter |
| Infraestrutura | Docker Compose, Nginx, GitHub Actions, GHCR |

## Problema

Equipes técnicas precisam identificar indisponibilidade e degradação antes que esses problemas afetem usuários por longos períodos. O Sentinela centraliza o cadastro dos serviços monitorados, executa verificações automáticas e registra dados operacionais para investigação.

## Funcionalidades

- Cadastro e gerenciamento de serviços monitorados.
- Verificações HTTP automáticas em intervalo configurável.
- Classificação dos serviços como online, offline ou degradado.
- Histórico persistente de verificações.
- Dashboard operacional.
- Autenticação JWT e controle de acesso por perfil.
- Métricas HTTP expostas para o Prometheus.
- Dashboards provisionados no Grafana.
- Logs centralizados com Loki e Promtail.
- Métricas de host e containers com Node Exporter e cAdvisor.
- Proxy reverso com Nginx.
- Pipeline de build e publicação de imagens no GHCR.

## Arquitetura

```text
Usuário -> Nginx -> React
                 -> FastAPI -> PostgreSQL
                                |
Worker de monitoramento --------+

Prometheus -> FastAPI + cAdvisor + Node Exporter
Grafana    -> Prometheus + Loki
Promtail   -> Loki
```

## Regras de monitoramento

- Resposta HTTP entre `200` e `399`: serviço online.
- Erro de rede, timeout ou resposta fora dessa faixa: serviço offline.
- Resposta bem-sucedida acima do limite configurado: serviço degradado.

Cada verificação registra o serviço, status calculado, código HTTP, tempo de resposta, mensagem de erro e data da execução.

## Perfis de acesso

| Perfil | Permissões |
| --- | --- |
| `ADMIN` | Gerencia usuários e serviços e acessa todas as visões operacionais |
| `OPERATOR` | Gerencia serviços e acompanha o monitoramento |
| `VIEWER` | Consulta dashboard, serviços e histórico |

## Como executar

```bash
cp .env.example .env
docker compose up -d --build
```

URLs principais:

- Aplicação: http://localhost
- API: http://localhost/api
- Health check: http://localhost/health
- Métricas: http://localhost/metrics
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

O backend aplica as migrações do Alembic durante a inicialização.

## Endpoints

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `POST` | `/api/auth/login` | Autentica o usuário |
| `GET` | `/api/auth/me` | Retorna o usuário autenticado |
| `GET` | `/api/users` | Lista usuários |
| `POST` | `/api/users` | Cria um usuário |
| `PUT` | `/api/users/{id}` | Atualiza um usuário |
| `PATCH` | `/api/users/{id}/activation` | Ativa ou desativa um usuário |
| `GET` | `/api/services` | Lista serviços monitorados |
| `POST` | `/api/services` | Cadastra um serviço |
| `GET` | `/api/services/{id}` | Detalha um serviço |
| `PUT` | `/api/services/{id}` | Atualiza um serviço |
| `PATCH` | `/api/services/{id}/activation` | Ativa ou desativa o monitoramento |
| `GET` | `/api/services/{id}/checks` | Lista verificações do serviço |
| `GET` | `/api/dashboard` | Retorna os dados operacionais |
| `GET` | `/health` | Verifica a saúde da API |
| `GET` | `/metrics` | Expõe métricas Prometheus |

## Estrutura

```text
backend/   API, regras de negócio, persistência e worker de monitoramento
frontend/  Dashboard operacional em React
infra/     Nginx, Prometheus, Grafana, Loki e Promtail
.github/   Pipeline de integração e publicação
```

## Validação

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

**MVP concluído.**

O primeiro escopo cobre monitoramento automático, histórico, dashboard, RBAC, métricas, logs e execução containerizada. Tracing distribuído, alertas e notificações permanecem como evoluções futuras.
