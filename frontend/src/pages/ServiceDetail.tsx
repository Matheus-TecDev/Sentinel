import { useEffect, useState } from "react";
import { ArrowLeft, Edit3, Power, RadioTower, Timer, Wifi } from "lucide-react";

import type { PageProps } from "../App";
import { apiRequest } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { Loading } from "../components/Loading";
import { StatCard } from "../components/StatCard";
import { StatusBadge } from "../components/StatusBadge";
import type { HealthCheckResult, ServiceDetail } from "../types";
import { environmentLabel, formatDate, formatMs, formatPercent, visualStatus } from "../utils";

interface ServiceDetailPageProps extends PageProps {
  serviceId: number;
}

export function ServiceDetailPage({ serviceId, navigate }: ServiceDetailPageProps) {
  const { token, canManageServices } = useAuth();
  const [service, setService] = useState<ServiceDetail | null>(null);
  const [checks, setChecks] = useState<HealthCheckResult[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load(): Promise<void> {
    try {
      setLoading(true);
      setError("");
      const [detail, history] = await Promise.all([
        apiRequest<ServiceDetail>(`/services/${serviceId}`, {}, token),
        apiRequest<HealthCheckResult[]>(`/services/${serviceId}/checks?limit=50`, {}, token)
      ]);
      setService(detail);
      setChecks(history);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar detalhes do serviço");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [serviceId, token]);

  async function toggleActive(): Promise<void> {
    if (!service) return;
    try {
      await apiRequest<ServiceDetail>(
        `/services/${service.id}/activation`,
        {
          method: "PATCH",
          body: JSON.stringify({ is_active: !service.is_active })
        },
        token
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar serviço");
    }
  }

  if (loading) return <Loading />;

  if (!service) {
    return (
      <div className="page-stack">
        <ErrorBanner message={error || "Serviço não encontrado"} />
      </div>
    );
  }

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Detalhes do serviço</span>
          <h2>{service.name}</h2>
        </div>
        <div className="button-row">
          <button className="secondary-button" onClick={() => navigate("/services")}>
            <ArrowLeft size={16} aria-hidden="true" />
            Voltar
          </button>
          {canManageServices && (
            <>
              <button className="secondary-button" onClick={() => navigate(`/services/${service.id}/edit`)}>
                <Edit3 size={16} aria-hidden="true" />
                Editar
              </button>
              <button className="secondary-button" onClick={toggleActive}>
                <Power size={16} aria-hidden="true" />
                {service.is_active ? "Desativar" : "Ativar"}
              </button>
            </>
          )}
        </div>
      </div>

      <ErrorBanner message={error} />

      <section className="stats-grid compact">
        <StatCard title="Status atual" value={<StatusText service={service} />} helper="última verificação" icon={Wifi} />
        <StatCard title="Resposta média" value={formatMs(service.average_response_time_ms)} helper="histórico do serviço" icon={Timer} />
        <StatCard title="Uptime" value={formatPercent(service.uptime_percent)} helper="online + degradado" icon={RadioTower} />
      </section>

      <section className="detail-grid">
        <div className="panel">
          <div className="panel-heading">
            <div>
              <h3>Dados principais</h3>
              <span>Configuração usada nas verificações automáticas</span>
            </div>
          </div>
          <dl className="detail-list">
            <div>
              <dt>Status</dt>
              <dd>
                <StatusBadge status={visualStatus(service)} />
              </dd>
            </div>
            <div>
              <dt>URL monitorada</dt>
              <dd className="break-text">{service.healthcheck_url}</dd>
            </div>
            <div>
              <dt>Responsável</dt>
              <dd>{service.owner}</dd>
            </div>
            <div>
              <dt>Ambiente</dt>
              <dd>{environmentLabel(service.environment)}</dd>
            </div>
            <div>
              <dt>Último HTTP</dt>
              <dd>{service.last_http_status_code ?? "Sem registro"}</dd>
            </div>
            <div>
              <dt>Última verificação</dt>
              <dd>{formatDate(service.last_checked_at)}</dd>
            </div>
          </dl>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <div>
              <h3>Falhas recentes</h3>
              <span>Ocorrências offline deste serviço</span>
            </div>
          </div>
          {service.recent_failures.length === 0 ? (
            <EmptyState title="Sem falhas recentes" message="Nenhum evento offline para este serviço." />
          ) : (
            <div className="failure-list">
              {service.recent_failures.map((failure) => (
                <div className="failure-item" key={failure.id}>
                  <StatusBadge status="offline" />
                  <div>
                    <strong>{failure.http_status_code ?? "Sem HTTP"}</strong>
                    <span>{failure.error_message ?? "Falha sem mensagem detalhada"}</span>
                  </div>
                  <time>{formatDate(failure.checked_at)}</time>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h3>Últimas verificações</h3>
            <span>Histórico operacional persistido no PostgreSQL</span>
          </div>
        </div>
        {checks.length === 0 ? (
          <EmptyState title="Sem histórico" message="Ainda não há verificações registradas para este serviço." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Status</th>
                  <th>HTTP</th>
                  <th>Tempo</th>
                  <th>Erro</th>
                  <th>Checado em</th>
                </tr>
              </thead>
              <tbody>
                {checks.map((check) => (
                  <tr key={check.id}>
                    <td>
                      <StatusBadge status={check.status} />
                    </td>
                    <td>{check.http_status_code ?? "Sem registro"}</td>
                    <td>{formatMs(check.response_time_ms)}</td>
                    <td>{check.error_message ?? "-"}</td>
                    <td>{formatDate(check.checked_at)}</td>
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

function StatusText({ service }: { service: ServiceDetail }) {
  return <StatusBadge status={visualStatus(service)} />;
}
