import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/services/apiClient";
import type { Decision } from "@/types/decision";

export type DecisionHistoryStatus = "idle" | "loading" | "success" | "error" | "empty";

export interface DecisionHistoryState {
  status: DecisionHistoryStatus;
  decisions: Decision[];
  errorMessage: string | null;
  refresh: () => void;
}

/**
 * Fetches recent decision history for a microgrid
 * (GET /api/decision/microgrids/{id}/history) — the record of past
 * RECOMMENDATIONS, not commands. `refreshSignal` lets the caller force a
 * re-fetch (e.g. after a new optimization runs or a decision is
 * approved/rejected) without this hook needing to know about those
 * actions itself.
 */
export function useDecisionHistory(
  microgridId: string | null,
  limit = 8,
  refreshSignal?: string
): DecisionHistoryState {
  const [status, setStatus] = useState<DecisionHistoryStatus>("idle");
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!microgridId) {
      setStatus("idle");
      return;
    }
    setStatus("loading");
    apiClient
      .getDecisionHistory(microgridId, limit)
      .then((data) => {
        setDecisions(data);
        setStatus(data.length === 0 ? "empty" : "success");
        setErrorMessage(null);
      })
      .catch((err: unknown) => {
        setStatus("error");
        setErrorMessage(err instanceof Error ? err.message : "Failed to load decision history.");
      });
  }, [microgridId, limit]);

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [microgridId, limit, refreshSignal]);

  return { status, decisions, errorMessage, refresh };
}
