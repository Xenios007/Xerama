import "./ErrorBanner.css";

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="xr-error" role="alert">
      {message}
    </div>
  );
}
