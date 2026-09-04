import { useState } from "react";
import { Badge, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import type { DecisionHistoryState } from "@/hooks/useDecisionHistory";
import type { Decision } from "@/types/decision";

export interface DecisionHistoryPanelProps {
  state: DecisionHistoryState;
}

const MODE_TONE: Record<string, "online" | "warn" | "danger" | "neutral"> = {
  NORMAL_MODE: "online",
  ECO_MODE: "warn",
  EMERGENCY_MODE: "danger",
};

const ACTION_TONE: Record<string, "online" | "warn" | "neutral"> = {
  CHARGE: "online",
  DISCHARGE: "warn",
  IDLE: "neutral",
};

const APPROVAL_TONE: Record<string, "online" | "warn" | "danger" | "neutral"> = {
  PENDING: "neutral",
  APPROVED: "online",
  REJECTED: "danger",
};

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function summarizeLoads(decision: Decision): string {
  const active = decision.load_recommendations.filter((r) => r.action !== "MAINTAIN");
  if (active.length === 0) return "No load changes";
  const deferred = active.filter((r) => r.action === "DEFER").length;
  const runNow = active.filter((r) => r.action === "RUN_NOW").length;
  const parts: string[] = [];
  if (deferred > 0) parts.push(`${deferred} deferred`);
  if (runNow > 0) parts.push(`${runNow} run now`);
  return parts.join(", ");
}

/**
 * Compact decision timeline: lets a user compare recent RECOMMENDATIONS
 * (operating mode, battery action, load recommendations, approval status,
 * time) at a glance, and expand any one of them to see its full
 * explanation. This is a historical record, not a log of hardware
 * actions — every entry here is a decision-support recommendation,
 * exactly like the live DecisionPanel above it.
 */
export function DecisionHistoryPanel({ state }: DecisionHistoryPanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const { status, decisions, errorMessage, refresh } = state;

  return (
    <Card>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <h3 style={{ fontSize: 14 }}>Decision History</h3>
        <Badge tone="neutral">HISTORY</Badge>
      </div>

      {status === "idle" && (
        <EmptyState title="No microgrid selected" description="Load a scene to see its decision history." />
      )}
      {status === "loading" && <LoadingState message="Loading decision history..." />}
      {status === "empty" && (
        <EmptyState
          title="No decisions yet"
          description="Run an optimization above to start building a decision history for this microgrid."
        />
      )}
      {status === "error" && (
        <ErrorState
          title="Decision history unavailable"
          description={errorMessage ?? "Failed to load decision history."}
          onRetry={refresh}
        />
      )}

      {status === "success" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {decisions.map((d) => {
            const expanded = expandedId === d.id;
            return (
              <div key={d.id} style={{ borderBottom: "1px solid var(--color-border)", paddingBottom: 6 }}>
                <button
                  onClick={() => setExpandedId(expanded ? null : d.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    width: "100%",
                    background: "none",
                    border: "none",
                    padding: "4px 0",
                    cursor: "pointer",
                    textAlign: "left",
                    flexWrap: "wrap",
                  }}
                  aria-expanded={expanded}
                >
                  <span style={{ fontSize: 11, color: "var(--color-text-faint)", fontFamily: "var(--font-mono)", minWidth: 92 }}>
                    {formatTime(d.created_at)}
                  </span>
                  <Badge tone={MODE_TONE[d.operating_mode] ?? "neutral"}>{d.operating_mode.replace("_MODE", "")}</Badge>
                  <Badge tone={ACTION_TONE[d.recommended_battery_action] ?? "neutral"}>
                    {d.recommended_battery_action}
                  </Badge>
                  <Badge tone={APPROVAL_TONE[d.approval_status] ?? "neutral"}>{d.approval_status}</Badge>
                  <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{summarizeLoads(d)}</span>
                </button>

                {expanded && (
                  <div
                    style={{
                      marginTop: 6,
                      marginBottom: 4,
                      padding: "8px 10px",
                      background: "var(--color-bg)",
                      borderRadius: "var(--radius-md)",
                      display: "flex",
                      flexDirection: "column",
                      gap: 6,
                    }}
                  >
                    <p style={{ fontSize: 12, color: "var(--color-text-muted)", margin: 0 }}>
                      <strong style={{ color: "var(--color-text)" }}>Mode: </strong>
                      {d.operating_mode_reason}
                    </p>
                    <p style={{ fontSize: 12, color: "var(--color-text-muted)", margin: 0 }}>
                      <strong style={{ color: "var(--color-text)" }}>Decision: </strong>
                      {d.explanation}
                    </p>
                    {d.load_recommendations.filter((r) => r.action !== "MAINTAIN").length > 0 && (
                      <div>
                        {d.load_recommendations
                          .filter((r) => r.action !== "MAINTAIN")
                          .map((r) => (
                            <div key={r.load_id} style={{ fontSize: 11, marginTop: 2 }}>
                              <Badge tone={r.action === "DEFER" ? "warn" : "online"}>{r.action}</Badge>{" "}
                              <span style={{ color: "var(--color-text-muted)" }}>
                                {r.load_name} — {r.reason}
                              </span>
                            </div>
                          ))}
                      </div>
                    )}
                    <p style={{ fontSize: 10, color: "var(--color-text-faint)", margin: 0 }}>{d.safety_note}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
