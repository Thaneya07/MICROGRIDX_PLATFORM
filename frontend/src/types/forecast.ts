/** Mirrors app/schemas/forecast.py. Kept in its own module so forecast data is never structurally confusable with live/simulated telemetry. */

export type ForecastTarget = "DEMAND" | "SOLAR_GENERATION";

export interface ForecastPoint {
  timestamp: string;
  predicted_w: number;
  lower_95_w: number;
  upper_95_w: number;
}

export interface ForecastResponse {
  microgrid_id: string;
  target: ForecastTarget;
  dataset_source: "SIMULATED" | "HARDWARE";
  model_id: string;
  model_trained_at: string;
  start: string;
  end: string;
  interval_minutes: number;
  points: ForecastPoint[];
  data_provenance_note: string;
}
