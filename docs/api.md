# API

A API usa o prefixo `/api`. Com exceção do login e do health check, as rotas exigem token Bearer válido.

## Autenticação

| Método | Endpoint | Acesso | Descrição |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | Público | Autentica e retorna JWT |
| GET | `/api/auth/me` | Autenticado | Retorna o usuário atual |

## Usuários

Todas as operações são exclusivas de `ADMIN`.

| Método | Endpoint | Descrição |
| --- | --- | --- |
| GET | `/api/users` | Lista usuários |
| POST | `/api/users` | Cria usuário |
| PUT | `/api/users/{user_id}` | Atualiza usuário |
| PATCH | `/api/users/{user_id}/activation` | Ativa ou desativa usuário |

## Serviços e checks

Leitura exige `VIEWER`, `OPERATOR` ou `ADMIN`. Criação e alteração exigem `OPERATOR` ou `ADMIN`.

| Método | Endpoint | Descrição |
| --- | --- | --- |
| GET | `/api/services` | Lista e filtra serviços |
| POST | `/api/services` | Cadastra serviço |
| GET | `/api/services/{service_id}` | Retorna detalhes |
| PUT | `/api/services/{service_id}` | Atualiza serviço |
| PATCH | `/api/services/{service_id}/activation` | Altera ativação |
| GET | `/api/services/checks/history` | Histórico global |
| GET | `/api/services/checks/failures` | Falhas recentes |
| GET | `/api/services/{service_id}/checks` | Checks do serviço |
| GET | `/api/services/{service_id}/metrics` | Métricas por período |
| GET | `/api/services/{service_id}/incidents` | Incidentes do serviço |

A listagem aceita filtros por texto, ambiente, status e ativação. Os históricos possuem limites entre 1 e 500 registros.

## Alertas e notificações

| Método | Endpoint | Acesso | Descrição |
| --- | --- | --- | --- |
| GET | `/api/services/{service_id}/alerts` | Leitura | Lista canais |
| POST | `/api/services/{service_id}/alerts` | Operação | Cria canal |
| PUT | `/api/services/{service_id}/alerts/{alert_id}` | Operação | Atualiza canal |
| PATCH | `/api/services/{service_id}/alerts/{alert_id}/activation` | Operação | Altera ativação |
| GET | `/api/services/{service_id}/notifications` | Leitura | Lista tentativas de entrega |

Os tipos modelados são `webhook`, `discord` e `email`. Nesta versão, webhook e Discord são enviados; e-mail registra falha informando que SMTP ainda não foi implementado.

## Dashboard e operação

| Método | Endpoint | Acesso | Descrição |
| --- | --- | --- | --- |
| GET | `/api/dashboard` | Autenticado | Resumo operacional |
| GET | `/health` | Público | Saúde da API |
| GET | `/metrics` | Infraestrutura | Métricas Prometheus |

Rotas adicionais de incidentes e responsáveis são registradas nos respectivos módulos da API.

## Erros

- `401`: token ausente, inválido, expirado ou usuário inativo;
- `403`: perfil sem permissão;
- `404`: recurso inexistente;
- `422`: contrato de entrada inválido.

A aplicação registra handlers próprios para erros HTTP e de validação.
