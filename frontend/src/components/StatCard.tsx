import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: ReactNode;
  helper: string;
  icon: LucideIcon;
  tone?: "neutral" | "good" | "warn" | "bad";
}

export function StatCard({ title, value, helper, icon: Icon, tone = "neutral" }: StatCardProps) {
  return (
    <section className={`stat-card ${tone}`}>
      <div className="stat-icon">
        <Icon size={20} aria-hidden="true" />
      </div>
      <span>{title}</span>
      <strong>{value}</strong>
      <small>{helper}</small>
    </section>
  );
}
