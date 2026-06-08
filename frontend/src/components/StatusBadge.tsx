import { AlertCircle, Ban, CheckCircle2, CircleDashed, Clock3 } from "lucide-react";

import type { HealthStatus } from "../types";

type VisualStatus = HealthStatus | "inactive" | "unknown";

const labels: Record<VisualStatus, string> = {
  online: "Online",
  offline: "Offline",
  degraded: "Degradado",
  inactive: "Inativo",
  unknown: "Sem verificações"
};

export function StatusBadge({ status }: { status: VisualStatus }) {
  const Icon =
    status === "online"
      ? CheckCircle2
      : status === "offline"
        ? AlertCircle
        : status === "degraded"
          ? Clock3
          : status === "inactive"
            ? Ban
            : CircleDashed;

  return (
    <span className={`status-badge ${status}`}>
      <Icon size={14} aria-hidden="true" />
      {labels[status]}
    </span>
  );
}
