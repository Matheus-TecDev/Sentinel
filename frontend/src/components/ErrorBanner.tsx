import { AlertTriangle } from "lucide-react";

export function ErrorBanner({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div className="error-banner" role="alert">
      <AlertTriangle size={18} aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}
