import { HTMLAttributes } from "react";
import "./Badge.css";

export type BadgeTone = "neutral" | "online" | "warn" | "danger" | "accent";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

/** Small labeled tag, e.g. for a device type or load category. */
export function Badge({ tone = "neutral", className = "", ...props }: BadgeProps) {
  const classes = ["mgx-badge", `mgx-badge--${tone}`, className].filter(Boolean).join(" ");
  return <span className={classes} {...props} />;
}
