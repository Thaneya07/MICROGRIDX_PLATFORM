import { API_BASE_URL } from "./config";
import type {
  ApiErrorBody,
  DatabaseHealthResponse,
  HealthResponse,
} from "@/types/api";
import type { MicrogridSnapshot } from "@/types/telemetry";
import type {
  ForecastResponse,
  ForecastTarget,
} from "@/types/forecast";
import type { EnergySummaryResponse } from "@/types/analytics";
import type { Decision } from "@/types/decision";
import type {
  DemoSeedResponse,
  MicrogridSummary,
} from "@/types/microgrid";

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: Record<string, unknown>;

  constructor(
    status: number,
    message: string,
    code?: string,
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(
    `${API_BASE_URL}${path}`,
    {
      headers: {
        "Content-Type": "application/json",
      },
      ...init,
    }
  );

  if (!response.ok) {
    let body: Partial<ApiErrorBody> = {};

    try {
      body = await response.json();
    } catch {
      // Response body was not JSON.
    }

    throw new ApiError(
      response.status,
      body.error?.message ??
        `Request failed with status ${response.status}`,
      body.error?.code,
      body.error?.details
    );
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  getHealth: () =>
    request<HealthResponse>(
      "/api/health"
    ),

  getDatabaseHealth: () =>
    request<DatabaseHealthResponse>(
      "/api/health/database"
    ),

  // Microgrid visualization snapshot
  getMicrogridSnapshot: (
    microgridId: string
  ) =>
    request<MicrogridSnapshot>(
      `/api/telemetry/microgrids/${microgridId}/snapshot`
    ),

  // Physical ESP32 hardware telemetry
  getHardwareTelemetry: (
    deviceId: string
  ) =>
    request<{
      device_id: string;
      recorded_at: string;
      temperature_c: number | null;
      humidity_percent: number | null;
      voltage_v: number;
      current_a: number;
      power_w: number;
      status: string;
      source: string;
    }>(
      `/api/telemetry/devices/${deviceId}/current`
    ),

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
      )}&end=${encodeURIComponent(
        end
      )}&interval_minutes=${intervalMinutes}`
    ),

  trainForecast: (
    microgridId: string,
    target: ForecastTarget,
    source = "SIMULATED"
  ) =>
    request<{
      target: ForecastTarget;
      source: string;
      model_type: string;
      trained_at: string;
    }>(
      `/api/forecast/microgrids/${microgridId}/train?target=${target}&source=${source}`,
      {
        method: "POST",
      }
    ),

  getEnergySummary: (
    microgridId: string,
    start?: string,
    end?: string
  ) => {
    const params = new URLSearchParams();

    if (start) {
      params.set("start", start);
    }

    if (end) {
      params.set("end", end);
    }

    const query = params.toString()
      ? `?${params.toString()}`
      : "";

    return request<EnergySummaryResponse>(
      `/api/energy/microgrids/${microgridId}/summary${query}`
    );
  },

  getLatestDecision: (
    microgridId: string
  ) =>
    request<Decision>(
      `/api/decision/microgrids/${microgridId}/latest`
    ),

  optimizeDecision: (
    microgridId: string
  ) =>
    request<Decision>(
      `/api/decision/microgrids/${microgridId}/optimize`,
      {
        method: "POST",
      }
    ),

  approveDecision: (
    decisionId: string,
    approved: boolean
  ) =>
    request<Decision>(
      `/api/decision/${decisionId}/approve`,
      {
        method: "POST",
        body: JSON.stringify({
          approved,
        }),
      }
    ),

  getDecisionHistory: (
    microgridId: string,
    limit = 8
  ) =>
    request<Decision[]>(
      `/api/decision/microgrids/${microgridId}/history?limit=${limit}`
    ),

  listMicrogrids: () =>
    request<MicrogridSummary[]>(
      "/api/microgrids"
    ),

  seedDemoMicrogrid: () =>
    request<DemoSeedResponse>(
      "/api/demo/seed",
      {
        method: "POST",
      }
    ),
};

/**
 * WebSocket URL for the live telemetry stream.
 * Derived from API_BASE_URL (http(s) -> ws(s)).
 */
export function getTelemetryStreamUrl(
  microgridId: string,
  intervalSeconds = 3
): string {
  const wsBase =
    API_BASE_URL.replace(/^http/, "ws");

  return `${wsBase}/api/telemetry/microgrids/${microgridId}/stream?interval_seconds=${intervalSeconds}`;
}