import type { ReactNode } from "react";
import { ApiError } from "../../api/client";
import { ErrorBanner } from "./ErrorBanner";
import { LoadingSpinner } from "./LoadingSpinner";

/**
 * The one loading/error pattern every page uses around a TanStack Query
 * result, so each page doesn't re-implement its own spinner/error UI.
 */
interface QueryStateProps {
  isLoading: boolean;
  error: unknown;
  children: ReactNode;
}

export function QueryState({ isLoading, error, children }: QueryStateProps) {
  if (isLoading) {
    return <LoadingSpinner />;
  }
  if (error) {
    const message = error instanceof ApiError ? error.detail : "Something went wrong.";
    return <ErrorBanner message={message} />;
  }
  return <>{children}</>;
}
