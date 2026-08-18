import { Badge, Card, EmptyState, ErrorState, LoadingState, MetricCard } from "@/components/ui";
import type { EnergySummaryState } from "@/hooks/useEnergySummary";

export interface AnalyticsOverlayProps {
  state: EnergySummaryState;
}

/** Compact dashboard of Step 4 analytics (renewable contribution, grid dependency, load factor, peak demand) around the 3D scene. Read-only, historical — distinct from the live scene. */
export function AnalyticsOverlay({ state }: AnalyticsOverlayProps) {
  return (
    <Card>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <h3 style={{ fontSize: 14 }}>Energy summary (24h)</h3>
        <Badge tone="neutral">ANALYTICS</Badge>
      </div>

      {state.status === "idle" && (
        <EmptyState title="No microgrid selected" description="Load a scene to see its energy summary." />
      )}
      {state.status === "loading" && <LoadingState message="Loading summary..." />}
      {state.status === "unavailable" && (
        <EmptyState
          title="Not enough history yet"
          description="This microgrid doesn't have enough persisted telemetry in the last 24h for a summary."
        />
      )}
      {state.status === "error" && (
        <ErrorState title="Summary unavailable" description={state.errorMessage ?? "Failed to load summary."} />
      )}
      {state.status === "success" && state.summary && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <MetricCard
            label="Renewable"
            value={state.summary.renewable_contribution_pct?.toFixed(0) ?? "—"}
            unit="%"
          />
          <MetricCard label="Grid dependency" value={state.summary.grid_dependency_pct?.toFixed(0) ?? "—"} unit="%" />
          <MetricCard label="Load factor" value={state.summary.load_factor?.toFixed(2) ?? "—"} />
          <MetricCard label="Peak demand" value={state.summary.peak_demand_w.toFixed(0)} unit="W" />
        </div>
      )}
    </Card>
  );
}
