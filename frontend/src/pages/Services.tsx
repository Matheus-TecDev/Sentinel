import { useCallback, useEffect, useMemo, useState } from "react";
import { Edit3, Plus, Power, Search, Server } from "lucide-react";

import type { PageProps } from "../App";
import { apiRequest } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { Loading } from "../components/Loading";
import { StatusBadge } from "../components/StatusBadge";
import type { HealthStatus, MonitoredService, ServiceEnvironment } from "../types";
import { environmentLabel, formatDate, formatMs, visualStatus } from "../utils";

type ActiveFilter = "" | "true" | "false";

export function ServicesPage({ navigate }: PageProps) {
  const { token, canManageServices } = useAuth();
  const [services, setServices] = useState<MonitoredService[]>([]);
  const [q, setQ] = useState("");
  const [environment, setEnvironment] = useState<ServiceEnvironment | "">("");
  const [status, setStatus] = useState<HealthStatus | "">("");
  const [active, setActive] = useState<ActiveFilter>("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    if (environment) params.set("environment", environment);
    if (status) params.set("status", status);
    if (active) params.set("is_active", active);
    const serialized = params.toString();
    return serialized ? `?${serialized}` : "";
  }, [active, environment, q, status]);

  const loadServices = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      setServices(await apiRequest<MonitoredService[]>(`/services${query}`, {}, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar serviços");
    } finally {
      setLoading(false);
    }
  }, [query, token]);

  useEffect(() => {
    void loadServices();
  }, [loadServices]);

  async function toggleService(service: MonitoredService): Promise<void> {
    try {
      await apiRequest<MonitoredService>(
        `/services/${service.id}/activation`,
        {
          method: "PATCH",
          body: JSON.stringify({ is_active: !service.is_active })
        },
        token
      );
      await loadServices();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar serviço");
    }
  }

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Aplicações monitoradas</span>
          <h2>Serviços monitorados</h2>
        </div>
        {canManageServices && (
          <button className="primary-button fit" onClick={() => navigate("/services/new")}>
            <Plus size={16} aria-hidden="true" />
            Novo serviço
          </button>
        )}
      </div>

      <ErrorBanner message={error} />

      <section className="toolbar">
        <label className="search-input">
          <Search size={16} aria-hidden="true" />
          <input placeholder="Pesquisar por nome" value={q} onChange={(event) => setQ(event.target.value)} />
        </label>
        <select value={environment} onChange={(event) => setEnvironment(event.target.value as ServiceEnvironment | "")}>
          <option value="">Todos os ambientes</option>
          <option value="dev">Dev</option>
          <option value="staging">Staging</option>
          <option value="production">Produção</option>
        </select>
        <select value={status} onChange={(event) => setStatus(event.target.value as HealthStatus | "")}>
          <option value="">Todos os status</option>
          <option value="online">Online</option>
          <option value="offline">Offline</option>
          <option value="degraded">Degradado</option>
        </select>
        <select value={active} onChange={(event) => setActive(event.target.value as ActiveFilter)}>
          <option value="">Ativos e inativos</option>
          <option value="true">Somente ativos</option>
          <option value="false">Somente inativos</option>
        </select>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h3>Serviços monitorados</h3>
            <span>Controle de verificações, responsáveis e ambientes</span>
          </div>
        </div>
        {loading ? (
          <Loading />
        ) : services.length === 0 ? (
          <EmptyState title="Nenhum serviço encontrado" message="Ajuste os filtros ou cadastre uma nova aplicação." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Ambiente</th>
                  <th>Status</th>
                  <th>HTTP</th>
                  <th>Tempo</th>
                  <th>Última verificação</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {services.map((service) => (
                  <tr key={service.id}>
                    <td onClick={() => navigate(`/services/${service.id}`)}>
                      <strong>{service.name}</strong>
                      <span>{service.healthcheck_url}</span>
                    </td>
                    <td>{environmentLabel(service.environment)}</td>
                    <td>
                      <StatusBadge status={visualStatus(service)} />
                    </td>
                    <td>{service.last_http_status_code ?? "Sem registro"}</td>
                    <td>{formatMs(service.last_response_time_ms)}</td>
                    <td>{formatDate(service.last_checked_at)}</td>
                    <td>
                      <div className="row-actions">
                        <button className="icon-button" onClick={() => navigate(`/services/${service.id}`)} title="Detalhes">
                          <Server size={16} aria-hidden="true" />
                        </button>
                        {canManageServices && (
                          <>
                            <button className="icon-button" onClick={() => navigate(`/services/${service.id}/edit`)} title="Editar">
                              <Edit3 size={16} aria-hidden="true" />
                            </button>
                            <button className="icon-button" onClick={() => toggleService(service)} title="Ativar ou desativar">
                              <Power size={16} aria-hidden="true" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
