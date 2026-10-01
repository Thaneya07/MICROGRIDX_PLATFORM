import { useCallback, useEffect, useState } from "react";
import type {
  ForecastResponse,
  ForecastTarget,
} from "@/types/forecast";


export type ForecastFetchStatus =
  | "idle"
  | "loading"
  | "success"
  | "error"
  | "unavailable";


export interface ForecastState {
  status: ForecastFetchStatus;
  forecast: ForecastResponse | null;
  errorMessage: string | null;
}


const API_BASE =
  import.meta.env.VITE_API_URL ??
  "http://127.0.0.1:8000";


export function useForecast(
  microgridId: string | null,
  target: ForecastTarget,
  horizonHours = 12,
  refreshKey = 0,
): ForecastState {

  const [status, setStatus] =
    useState<ForecastFetchStatus>("idle");

  const [forecast, setForecast] =
    useState<ForecastResponse | null>(null);

  const [errorMessage, setErrorMessage] =
    useState<string | null>(null);


  const fetchForecast = useCallback(
    async () => {

      if (!microgridId) {
        setStatus("idle");
        setForecast(null);
        return;
      }

      setStatus("loading");
      setErrorMessage(null);


      try {

        /*
         * Demand dataset is 30-minute data.
         * 12 hours = 24 points.
         */
        const points =
          target === "DEMAND"
            ? Math.max(
                1,
                Math.round(
                  horizonHours * 2
                ),
              )
            : /*
               * Solar dataset is 5-minute data.
               * 12 hours = 144 points.
               */
              Math.max(
                1,
                Math.round(
                  horizonHours * 12
                ),
              );


        const endpoint =
          target === "DEMAND"
            ? `${API_BASE}/api/ai-forecasts/replay/demand?points=${points}`
            : `${API_BASE}/api/ai-forecasts/replay/solar?points=${points}`;


        const response =
          await fetch(endpoint);


        if (!response.ok) {
          const detail =
            await response.text();

          throw new Error(
            detail ||
              `AI forecast API returned ${response.status}`,
          );
        }


        const replay =
          await response.json();


        const now =
          new Date();

        const firstTimestamp =
          replay.points?.[0]?.timestamp ??
          now.toISOString();

        const lastTimestamp =
          replay.points?.[
            replay.points.length - 1
          ]?.timestamp ??
          now.toISOString();


        const data: ForecastResponse = {
          microgrid_id:
            microgridId,

          target,

          dataset_source:
            "SIMULATED",

          model_id:
            target === "DEMAND"
              ? "enhanced_random_forest"
              : "solar_random_forest",

          model_trained_at:
            now.toISOString(),

          start:
            firstTimestamp,

          end:
            lastTimestamp,

          interval_minutes:
            target === "DEMAND"
              ? 30
              : 5,

          points:
            replay.points,

          data_provenance_note:
            replay.data_provenance_note ??
            "Historical AI model replay using prepared dataset rows.",
        };


        setForecast(data);
        setStatus("success");
        setErrorMessage(null);

      } catch (err: unknown) {

        const message =
          err instanceof Error
            ? err.message
            : "Failed to fetch AI forecast.";

        setStatus("error");
        setErrorMessage(message);

      }

    },
    [
      microgridId,
      target,
      horizonHours,
      refreshKey,
    ],
  );


  useEffect(() => {
    void fetchForecast();
  }, [fetchForecast]);


  return {
    status,
    forecast,
    errorMessage,
  };
}