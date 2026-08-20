import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/services/apiClient";
import type { Decision } from "@/types/decision";

export type DecisionFetchStatus = "idle" | "loading" | "success" | "error" | "unavailable" | "optimizing";

export interface DecisionState {
  status: DecisionFetchStatus;
  decision: Decision | null;
  errorMessage: string | null;
  runOptimization: () => void;
  approve: (approved: boolean) => void;
}

/**
 * Fetches the latest Decision Engine recommendation for a microgrid, and
 * exposes an action to trigger a fresh optimization run. This is a
 * decision-support display only — nothing here (or anywhere in the
 * frontend) sends a command to physical hardware; approve() only records
 * a human approval/rejection status via the backend's read-only-effect
 * endpoint.
 */
export function useDecision(microgridId: string | null): DecisionState {
  const [status, setStatus] = useState<DecisionFetchStatus>("idle");
  const [decision, setDecision] = useState<Decision | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchLatest = useCallback(() => {
    if (!microgridId) {
      setStatus("idle");
      return;
    }
    setStatus("loading");
    apiClient
      .getLatestDecision(microgridId)
      .then((data) => {
        setDecision(data);
        setStatus("success");
        setErrorMessage(null);
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Failed to fetch decision.";
        if (message.toLowerCase().includes("no decision exists")) {
          setStatus("unavailable");
        } else {
          setStatus("error");
        }
        setErrorMessage(message);
      });
  }, [microgridId]);

  useEffect(() => {
    fetchLatest();
  }, [fetchLatest]);

  const runOptimization = useCallback(() => {
    if (!microgridId) return;
    setStatus("optimizing");
    apiClient
      .optimizeDecision(microgridId)
      .then((data) => {
        setDecision(data);
        setStatus("success");
        setErrorMessage(null);
      })
      .catch((err: unknown) => {
        setStatus("error");
        setErrorMessage(err instanceof Error ? err.message : "Failed to run optimization.");
      });
  }, [microgridId]);

  const approve = useCallback(
    (approved: boolean) => {
      if (!decision) return;
      apiClient
        .approveDecision(decision.id, approved)
        .then((data) => setDecision(data))
        .catch((err: unknown) => {
          setErrorMessage(err instanceof Error ? err.message : "Failed to record approval.");
        });
    },
    [decision]
  );

  return { status, decision, errorMessage, runOptimization, approve };
}
