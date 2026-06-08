import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, Save } from "lucide-react";

import type { PageProps } from "../App";
import { apiRequest } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ErrorBanner } from "../components/ErrorBanner";
import { Loading } from "../components/Loading";
import type { ServiceDetail, ServiceEnvironment, ServicePayload } from "../types";

interface ServiceFormPageProps extends PageProps {
  mode: "create" | "edit";
  serviceId?: number;
}

const initialForm: ServicePayload = {
  name: "",
  description: "",
  environment: "production",
  healthcheck_url: "",
  owner: "",
  is_active: true
};

export function ServiceFormPage({ mode, serviceId, navigate }: ServiceFormPageProps) {
  const { token, canManageServices } = useAuth();
  const [form, setForm] = useState<ServicePayload>(initialForm);
  const [loading, setLoading] = useState(mode === "edit");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load(): Promise<void> {
      if (mode !== "edit" || !serviceId) return;
      try {
        setLoading(true);
        const service = await apiRequest<ServiceDetail>(`/services/${serviceId}`, {}, token);
        setForm({
          name: service.name,
          description: service.description ?? "",
          environment: service.environment,
          healthcheck_url: service.healthcheck_url,
          owner: service.owner,
          is_active: service.is_active
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Falha ao carregar serviço");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [mode, serviceId, token]);

  function updateField<K extends keyof ServicePayload>(field: K, value: ServicePayload[K]): void {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError("");
    setSaving(true);
    const payload: ServicePayload = {
      ...form,
      description: form.description?.trim() ? form.description : null
    };

    try {
      const endpoint = mode === "edit" && serviceId ? `/services/${serviceId}` : "/services";
      const method = mode === "edit" ? "PUT" : "POST";
      const saved = await apiRequest<ServiceDetail>(
        endpoint,
        {
          method,
          body: JSON.stringify(payload)
        },
        token
      );
      navigate(`/services/${saved.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar serviço");
    } finally {
      setSaving(false);
    }
  }

  if (!canManageServices) {
    return (
      <div className="page-stack">
        <ErrorBanner message="Seu perfil não permite gerenciar serviços." />
      </div>
    );
  }

  if (loading) return <Loading />;

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Configuração do serviço</span>
          <h2>{mode === "edit" ? "Editar serviço" : "Novo serviço"}</h2>
        </div>
        <button className="secondary-button" onClick={() => navigate("/services")}>
          <ArrowLeft size={16} aria-hidden="true" />
          Voltar
        </button>
      </div>

      <ErrorBanner message={error} />

      <form className="panel form-grid" onSubmit={handleSubmit}>
        <label>
          Nome
          <input value={form.name} onChange={(event) => updateField("name", event.target.value)} required />
        </label>
        <label>
          Responsável
          <input value={form.owner} onChange={(event) => updateField("owner", event.target.value)} required />
        </label>
        <label>
          Ambiente
          <select
            value={form.environment}
            onChange={(event) => updateField("environment", event.target.value as ServiceEnvironment)}
          >
            <option value="dev">Dev</option>
            <option value="staging">Staging</option>
          <option value="production">Produção</option>
          </select>
        </label>
        <label>
          URL de verificação
          <input
            value={form.healthcheck_url}
            onChange={(event) => updateField("healthcheck_url", event.target.value)}
            placeholder="https://api.empresa.com.br/health"
            required
          />
        </label>
        <label className="wide">
          Descrição
          <textarea value={form.description ?? ""} onChange={(event) => updateField("description", event.target.value)} />
        </label>
        <label className="check-row">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(event) => updateField("is_active", event.target.checked)}
          />
          Ativo para verificação automática
        </label>
        <div className="form-actions wide">
          <button className="primary-button fit" disabled={saving}>
            <Save size={16} aria-hidden="true" />
            {saving ? "Salvando..." : "Salvar serviço"}
          </button>
        </div>
      </form>
    </div>
  );
}
