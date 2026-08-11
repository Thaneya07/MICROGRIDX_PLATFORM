import { HTMLAttributes, ReactNode } from "react";
import { Button } from "./Button";
import "./FeedbackStates.css";

export interface LoadingStateProps extends HTMLAttributes<HTMLDivElement> {
  message?: string;
}

/** Shown while data is being fetched. Never mixed with placeholder data. */
export function LoadingState({ message = "Loading...", className = "", ...props }: LoadingStateProps) {
  return (
    <div className={["mgx-feedback-state", className].filter(Boolean).join(" ")} {...props}>
      <span className="mgx-spinner" aria-hidden="true" />
      <p className="mgx-feedback-message">{message}</p>
    </div>
  );
}

export interface EmptyStateProps extends HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: string;
  action?: ReactNode;
}

/** Shown when a query legitimately returns no data — an invitation to act, not an apology. */
export function EmptyState({ title, description, action, className = "", ...props }: EmptyStateProps) {
  return (
    <div className={["mgx-feedback-state", className].filter(Boolean).join(" ")} {...props}>
      <p className="mgx-feedback-title">{title}</p>
      {description && <p className="mgx-feedback-message">{description}</p>}
      {action}
    </div>
  );
}

export interface ErrorStateProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  description?: string;
  onRetry?: () => void;
}

/** Shown on a failed request. States what happened plainly, offers a retry. */
export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
  className = "",
  ...props
}: ErrorStateProps) {
  return (
    <div className={["mgx-feedback-state", "mgx-feedback-state--error", className].filter(Boolean).join(" ")} {...props}>
      <p className="mgx-feedback-title">{title}</p>
      {description && <p className="mgx-feedback-message">{description}</p>}
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}
