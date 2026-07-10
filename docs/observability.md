# Observabilidade

## Métricas

A API usa `prometheus-fastapi-instrumentator` e expõe `/metrics`. A própria rota de métricas é excluída da instrumentação.

O Prometheus coleta a cada 15 segundos:

| Job | Target | Finalidade |
| --- | --- | --- |
| `sentinel-backend` | `backend:8000/metrics` | Requisições, status e latência |
| `cadvisor` | `cadvisor:8080` | Containers |
| `node-exporter` | `node-exporter:9100` | Host |

## Logs

O backend configura logging na inicialização e registra eventos operacionais, incluindo:

- início e encerramento da API;
- início e encerramento do worker;
- resultado dos health checks;
- falhas na entrega de alertas.

O Promtail descobre containers pelo socket do Docker, extrai seus logs e adiciona labels como container, serviço e projeto do Compose. Os registros são enviados ao Loki.

## Visualização

O Grafana utiliza datasources provisionados para consultar métricas e logs. Os volumes preservam dados do Grafana, Prometheus e Loki entre reinicializações.

## Health checks

- `GET /health`: confirma que o processo da API responde;
- health checks do Docker controlam a ordem de inicialização;
- o PostgreSQL usa `pg_isready`;
- backend e frontend possuem verificações próprias no Compose.

O endpoint `/health` não testa a conexão com PostgreSQL; ele indica apenas disponibilidade da API.

## Limitações

- Não há tracing distribuído.
- Não há Alertmanager na stack atual.
- Não há SLOs ou recording rules declarados.
- Retenção e dimensionamento são configurações locais.
- Promtail é suficiente para o MVP, mas pode ser substituído por Grafana Alloy em uma evolução.
