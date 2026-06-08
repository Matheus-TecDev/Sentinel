import { FormEvent, useState } from "react";
import { Activity, Lock, ShieldCheck } from "lucide-react";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ErrorBanner } from "../components/ErrorBanner";
import type { PageProps } from "../App";

export function Login({ navigate }: PageProps) {
  const { login } = useAuth();
  const [email, setEmail] = useState("admin@sentinel.local");
  const [password, setPassword] = useState("ChangeMe123!");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao autenticar");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-screen">
      <section className="login-visual" aria-label="Sentinel">
        <div className="login-brand">
          <div className="brand-mark large">
            <ShieldCheck size={32} aria-hidden="true" />
          </div>
          <div>
            <span>Sentinel</span>
            <strong>Central de Monitoramento de Serviços</strong>
          </div>
        </div>
        <div className="signal-board" aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
          <span />
        </div>
        <div className="login-metrics">
          <div>
            <Activity size={18} />
            <span>Verificações HTTP</span>
            <strong>Intervalo de 60 segundos</strong>
          </div>
          <div>
            <Lock size={18} />
            <span>RBAC</span>
            <strong>ADMIN / OPERATOR / VIEWER</strong>
          </div>
        </div>
      </section>

      <section className="login-panel">
        <div className="login-copy">
          <span className="eyebrow">Acesso à plataforma</span>
          <h1>Monitore serviços e identifique falhas antes que impactem a operação.</h1>
        </div>
        <ErrorBanner message={error} />
        <form className="form-stack" onSubmit={handleSubmit}>
          <label>
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" />
          </label>
          <label>
            Senha
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              autoComplete="current-password"
            />
          </label>
          <button className="primary-button" disabled={isSubmitting}>
            {isSubmitting ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}
