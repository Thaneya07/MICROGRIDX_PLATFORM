import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/services/apiClient";
import type { DatabaseHealthResponse, HealthResponse } from "@/types/api";

export type ConnectivityStatus = "idle" | "loading" | "success" | "error";

export interface BackendConnectivityState {
  status: ConnectivityStatus;
  api?: HealthResponse;
  database?: DatabaseHealthResponse;
  errorMessage?: string;
  checkedAt?: Date;
  refresh: () => void;
}

/** Exercises both health endpoints to confirm frontend/backend/database connectivity end to end. */
export function useBackendConnectivity(): BackendConnectivityState {
  const [status, setStatus] = useState<ConnectivityStatus>("idle");
  const [api, setApi] = useState<HealthResponse>();
  const [database, setDatabase] = useState<DatabaseHealthResponse>();
  const [errorMessage, setErrorMessage] = useState<string>();
  const [checkedAt, setCheckedAt] = useState<Date>();

  const refresh = useCallback(() => {
    setStatus("loading");
    setErrorMessage(undefined);

    Promise.all([apiClient.getHealth(), apiClient.getDatabaseHealth()])
      .then(([healthResult, dbResult]) => {
        setApi(healthResult);
        setDatabase(dbResult);
        setStatus("success");
        setCheckedAt(new Date());
      })
      .catch((err: unknown) => {
        setStatus("error");
        setCheckedAt(new Date());
        setErrorMessage(err instanceof ApiError ? err.message : "Unable to reach the backend.");
      });
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { status, api, database, errorMessage, checkedAt, refresh };
}
