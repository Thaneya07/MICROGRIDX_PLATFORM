import { HTMLAttributes, ReactNode } from "react";
import { Card } from "./Card";
import "./MetricCard.css";

export interface MetricCardProps extends HTMLAttributes<HTMLDivElement> {
  label: string;
  value: ReactNode;
  unit?: string;
  trend?: ReactNode;
}

/** Panel-meter style readout. Presentation only — never fabricate the value passed in. */
export function MetricCard({ label, value, unit, trend, className = "", ...props }: MetricCardProps) {
  return (
    <Card className={["mgx-metric-card", className].filter(Boolean).join(" ")} {...props}>
      <div className="mgx-metric-label">{label}</div>
      <div className="mgx-metric-value">
        <span className="mgx-metric-value-number">{value}</span>
        {unit && <span className="mgx-metric-value-unit">{unit}</span>}
      </div>
      {trend && <div className="mgx-metric-trend">{trend}</div>}
    </Card>
  );
}
