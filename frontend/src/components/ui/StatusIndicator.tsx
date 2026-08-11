import { HTMLAttributes } from "react";
import "./StatusIndicator.css";

export type StatusTone = "online" | "offline" | "warn" | "danger";

export interface StatusIndicatorProps extends HTMLAttributes<HTMLSpanElement> {
  status: StatusTone;
  label?: string;
  pulse?: boolean;
}

const DEFAULT_LABELS: Record<StatusTone, string> = {
  online: "Online",
  offline: "Offline",
  warn: "Degraded",
  danger: "Fault",
};

/**
 * Instrumentation-style status LED, the signature element of the design
 * system: a small dot that pulses for live/online states, the way panel
 * indicator lights do on physical grid equipment.
 */
export function StatusIndicator({ status, label, pulse = true, className = "", ...props }: StatusIndicatorProps) {
  const classes = ["mgx-status", className].filter(Boolean).join(" ");
  return (
    <span className={classes} {...props}>
      <span className={`mgx-status-dot mgx-status-dot--${status}`}>
        {pulse && status === "online" && <span className="mgx-status-dot-ping" />}
      </span>
      <span className="mgx-status-label">{label ?? DEFAULT_LABELS[status]}</span>
    </span>
  );
}
