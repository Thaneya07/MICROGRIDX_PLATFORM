import { Badge, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import type { ForecastState } from "@/hooks/useForecast";

export interface ForecastPanelProps {
  title: string;
  state: ForecastState;
}

/**
 * Renders a forecast as a clearly-labeled, visually distinct panel — never
 * layered onto or blended with the live 3D scene / live metrics. Every
 * state (loading, unavailable, error, success) is handled explicitly.
 */
export function ForecastPanel({ title, state }: ForecastPanelProps) {
  return (
    <Card>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <h3 style={{ fontSize: 14 }}>{title}</h3>
        <Badge tone="accent">FORECAST</Badge>
      </div>

      {state.status === "loading" && <LoadingState message="Loading forecast..." />}

      {state.status === "unavailable" && (
        <EmptyState
          title="No forecast model trained yet"
          description="Train a model via POST /api/forecast/microgrids/{id}/train to see a forecast here."
        />
      )}

      {state.status === "error" && (
        <ErrorState title="Forecast unavailable" description={state.errorMessage ?? "Failed to load forecast."} />
      )}

      {state.status === "success" && state.forecast && (
        <div
          style={{ fontFamily: "var(--font-mono)", fontSize: 12, display: "flex", flexDirection: "column", gap: 6 }}
        >
          {state.forecast.points.slice(0, 6).map((p) => (
            <div
              key={p.timestamp}
              style={{ display: "flex", justifyContent: "space-between", color: "var(--color-text-muted)" }}
            >
              <span>{new Date(p.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
              <span style={{ color: "var(--color-text)" }}>
                {p.predicted_w.toFixed(0)}W
                <span style={{ opacity: 0.6 }}>
                  {" "}
                  ({p.lower_95_w.toFixed(0)}–{p.upper_95_w.toFixed(0)})
                </span>
              </span>
            </div>
          ))}
          <p style={{ fontSize: 11, color: "var(--color-text-faint)", marginTop: 4 }}>
            {state.forecast.data_provenance_note}
          </p>
        </div>
      )}
    </Card>
  );
}
