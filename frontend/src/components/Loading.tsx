export function Loading({ label = "Carregando dados" }: { label?: string }) {
  return (
    <div className="loading">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
