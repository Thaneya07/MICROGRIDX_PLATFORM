import { API_BASE_URL } from "./config";
import type { ApiErrorBody, DatabaseHealthResponse, HealthResponse } from "@/types/api";

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
};
