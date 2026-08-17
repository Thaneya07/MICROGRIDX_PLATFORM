import { Badge } from "@/components/ui";
import type { TelemetrySource } from "@/types/telemetry";

export interface DataSourceBadgeProps {
  source: TelemetrySource | null;
}

/** Always-visible indicator of whether displayed data is SIMULATED or HARDWARE. Never omitted, never ambiguous. */
export function DataSourceBadge({ source }: DataSourceBadgeProps) {
  if (!source) {
    return <Badge tone="neutral">NO DATA</Badge>;
  }
  if (source === "HARDWARE") {
    return <Badge tone="online">HARDWARE — live sensor data</Badge>;
  }
  return <Badge tone="warn">SIMULATED — not physical sensor data</Badge>;
}
