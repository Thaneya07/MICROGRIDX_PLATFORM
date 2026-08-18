import { useEffect, useState } from "react";
import { apiClient } from "@/services/apiClient";
import type { EnergySummaryResponse } from "@/types/analytics";

export type EnergySummaryStatus = "idle" | "loading" | "success" | "error" | "unavailable";

export interface EnergySummaryState {
  status: EnergySummaryStatus;
  summary: EnergySummaryResponse | null;
  errorMessage: string | null;
}

/**
 * Fetches the Step 4 analytics energy summary (renewable contribution,
 * grid dependency, load factor, peak demand) for the last 24h, for the
 * analytics overlay around the 3D scene. Independent of the live
 * telemetry stream — analytics reads persisted history, not the live tick.
 */
export function useEnergySummary(microgridId: string | null): EnergySummaryState {
  const [status, setStatus] = useState<EnergySummaryStatus>("idle");
  const [summary, setSummary] = useState<EnergySummaryResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!microgridId) {
      setStatus("idle");
      return;
    }
    setStatus("loading");
    apiClient
      .getEnergySummary(microgridId)
      .then((data) => {
        setSummary(data);
        setStatus("success");
        setErrorMessage(null);
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Failed to fetch energy summary.";
        if (message.toLowerCase().includes("insufficient")) {
          setStatus("unavailable");
        } else {
          setStatus("error");
        }
        setErrorMessage(message);
      });
  }, [microgridId]);

  return { status, summary, errorMessage };
}
