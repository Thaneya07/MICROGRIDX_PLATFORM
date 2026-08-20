import { Badge, Button, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import type { DecisionState } from "@/hooks/useDecision";

export interface DecisionPanelProps {
  state: DecisionState;
}

const STATUS_TONE: Record<string, "online" | "warn" | "danger" | "neutral"> = {
  OPTIMAL: "online",
  SAFE_FALLBACK: "warn",
  INFEASIBLE: "danger",
  ERROR: "danger",
};

const ACTION_TONE: Record<string, "online" | "warn" | "neutral"> = {
  CHARGE: "online",
  DISCHARGE: "warn",
  IDLE: "neutral",
};

/**
 * Decision Engine / Optimization panel. Every value here is explicitly
 * labeled RECOMMENDATION/OPTIMIZED — never presented as a live sensor
 * reading or an actual control action. See useDecision.ts and the
 * backend safety_note field for the full safety boundary.
 */
export function DecisionPanel({ state }: DecisionPanelProps) {
  const { status, decision, errorMessage, runOptimization, approve } = state;

  return (
    <Card>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <h3 style={{ fontSize: 14 }}>Decision Engine</h3>
        <Badge tone="accent">RECOMMENDATION</Badge>
      </div>

      {status === "idle" && (
        <EmptyState title="No microgrid selected" description="Load a scene to see optimization recommendations." />
      )}
      {status === "loading" && <LoadingState message="Loading latest recommendation..." />}
      {status === "unavailable" && (
        <>
          <EmptyState
            title="No recommendation yet"
            description="No optimization has been run for this microgrid yet."
          />
          <Button size="sm" onClick={runOptimization} style={{ marginTop: 8 }}>
            Run optimization now
          </Button>
        </>
      )}
      {status === "error" && (
        <ErrorState
          title="Decision Engine unavailable"
          description={errorMessage ?? "Failed to load a recommendation."}
          onRetry={runOptimization}
        />
      )}
      {status === "optimizing" && <LoadingState message="Running optimization..." />}

      {(status === "success") && decision && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Badge tone={STATUS_TONE[decision.optimization_status] ?? "neutral"}>
              {decision.optimization_status}
            </Badge>
            {decision.fallback_used && <Badge tone="warn">FALLBACK</Badge>}
            <Badge tone="neutral">{decision.source}</Badge>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Battery:</span>
            <Badge tone={ACTION_TONE[decision.recommended_battery_action] ?? "neutral"}>
              {decision.recommended_battery_action}
              {decision.recommended_battery_power_w
                ? ` ${decision.recommended_battery_power_w.toFixed(0)}W`
                : ""}
            </Badge>
          </div>

          <p style={{ fontSize: 12, color: "var(--color-text-muted)", margin: 0 }}>{decision.explanation}</p>

          {decision.load_recommendations.filter((r) => r.action !== "MAINTAIN").length > 0 && (
            <div>
              <p style={{ fontSize: 11, fontWeight: 600, color: "var(--color-text-muted)", marginBottom: 4 }}>
                Load recommendations
              </p>
              {decision.load_recommendations
                .filter((r) => r.action !== "MAINTAIN")
                .map((r) => (
                  <div key={r.load_id} style={{ fontSize: 12, marginBottom: 4 }}>
                    <Badge tone={r.action === "DEFER" ? "warn" : "online"}>{r.action}</Badge>{" "}
                    <span>{r.load_name}</span>
                  </div>
                ))}
            </div>
          )}

          <div style={{ display: "flex", gap: 8 }}>
            <span style={{ fontSize: 11, color: "var(--color-text-faint)" }}>
              Constraints: {decision.constraints_satisfied ? "all satisfied" : "violation detected"}
            </span>
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <Button size="sm" variant="secondary" onClick={runOptimization}>
              Re-optimize
            </Button>
            {decision.approval_status === "PENDING" && !decision.fallback_used && (
              <>
                <Button size="sm" onClick={() => approve(true)}>
                  Approve
                </Button>
                <Button size="sm" variant="ghost" onClick={() => approve(false)}>
                  Reject
                </Button>
              </>
            )}
            {decision.approval_status !== "PENDING" && (
              <Badge tone={decision.approval_status === "APPROVED" ? "online" : "danger"}>
                {decision.approval_status}
              </Badge>
            )}
          </div>

          <p style={{ fontSize: 10, color: "var(--color-text-faint)", marginTop: 4 }}>{decision.safety_note}</p>
        </div>
      )}
    </Card>
  );
}
