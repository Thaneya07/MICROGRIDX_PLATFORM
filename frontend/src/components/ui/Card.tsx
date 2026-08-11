import { HTMLAttributes } from "react";
import "./Card.css";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padded?: boolean;
}

/** Generic content panel. The base surface every other primitive sits on. */
export function Card({ padded = true, className = "", ...props }: CardProps) {
  const classes = ["mgx-card", padded ? "mgx-card--padded" : "", className].filter(Boolean).join(" ");
  return <div className={classes} {...props} />;
}
