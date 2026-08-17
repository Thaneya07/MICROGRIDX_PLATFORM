import { API_BASE_URL } from "./config";
import type { ApiErrorBody, DatabaseHealthResponse, HealthResponse } from "@/types/api";
import type { MicrogridSnapshot } from "@/types/telemetry";
import type { ForecastResponse, ForecastTarget } from "@/types/forecast";

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: Record<string, unknown>;

  constructor(status: number, message: string, code?: string, details?: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    let body: Partial<ApiErrorBody> = {};
    try {
      body = await response.json();
    } catch {
      // Response body was not JSON; fall through with a generic message.
    }
    throw new ApiError(
      response.status,
      body.error?.message ?? `Request failed with status ${response.status}`,
      body.error?.code,
      body.error?.details
    );
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  getHealth: () => request<HealthResponse>("/api/health"),
  getDatabaseHealth: () => request<DatabaseHealthResponse>("/api/health/database"),

  // Step 6 additions (3D visualization) — additive, existing methods above unchanged.
  getMicrogridSnapshot: (microgridId: string) =>
    request<MicrogridSnapshot>(`/api/telemetry/microgrids/${microgridId}/snapshot`),

  getForecast: (
    microgridId: string,
    target: ForecastTarget,
    start: string,
    end: string,
    intervalMinutes: number
  ) =>
    request<ForecastResponse>(
      `/api/forecast/microgrids/${microgridId}?target=${target}&start=${encodeURIComponent(
        start
      )}&end=${encodeURIComponent(end)}&interval_minutes=${intervalMinutes}`
    ),
};

/** WebSocket URL for the live telemetry stream, derived from API_BASE_URL (http(s) -> ws(s)). */
export function getTelemetryStreamUrl(microgridId: string, intervalSeconds = 3): string {
  const wsBase = API_BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/api/telemetry/microgrids/${microgridId}/stream?interval_seconds=${intervalSeconds}`;
}
