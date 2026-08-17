import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/services/apiClient";
import type { ForecastResponse, ForecastTarget } from "@/types/forecast";

export type ForecastFetchStatus = "idle" | "loading" | "success" | "error" | "unavailable";

export interface ForecastState {
  status: ForecastFetchStatus;
  forecast: ForecastResponse | null;
  errorMessage: string | null;
}

/**
 * Fetches a forecast for one target, covering a window starting "now" and
 * running `horizonHours` into the future. Deliberately independent of
 * useTelemetryStream — forecast data must never be merged into the live
 * snapshot state, per the product rule that forecast and live measurements
 * are always visually and structurally distinct.
 */
export function useForecast(microgridId: string | null, target: ForecastTarget, horizonHours = 12): ForecastState {
  const [status, setStatus] = useState<ForecastFetchStatus>("idle");
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchForecast = useCallback(() => {
    if (!microgridId) {
      setStatus("idle");
      return;
    }
    setStatus("loading");
    const start = new Date();
    const end = new Date(start.getTime() + horizonHours * 60 * 60 * 1000);

    apiClient
      .getForecast(microgridId, target, start.toISOString(), end.toISOString(), 30)
      .then((data) => {
        setForecast(data);
        setStatus("success");
        setErrorMessage(null);
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Failed to fetch forecast.";
        if (message.toLowerCase().includes("no trained")) {
          setStatus("unavailable");
        } else {
          setStatus("error");
        }
        setErrorMessage(message);
      });
  }, [microgridId, target, horizonHours]);

  useEffect(() => {
    fetchForecast();
  }, [fetchForecast]);

  return { status, forecast, errorMessage };
}
