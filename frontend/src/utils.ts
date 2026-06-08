import type { HealthStatus, MonitoredService } from "./types";

export function formatDate(value: string | null): string {
  if (!value) return "Sem registro";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

export function formatMs(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "Sem registro";
  return `${Math.round(value)} ms`;
}

export function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`;
}

export function visualStatus(service: MonitoredService): HealthStatus | "inactive" | "unknown" {
  if (!service.is_active) return "inactive";
  return service.current_status ?? "unknown";
}

export function environmentLabel(value: string): string {
  const labels: Record<string, string> = {
    dev: "Dev",
    staging: "Staging",
    production: "Produção"
  };
  return labels[value] ?? value;
}
