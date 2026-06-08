import { Inbox } from "lucide-react";

export function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="empty-state">
      <Inbox size={34} aria-hidden="true" />
      <strong>{title}</strong>
      <span>{message}</span>
    </div>
  );
}
