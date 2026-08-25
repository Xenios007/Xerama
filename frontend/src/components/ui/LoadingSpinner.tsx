import "./LoadingSpinner.css";

export function LoadingSpinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="xr-loading" role="status">
      <span className="xr-loading__spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
