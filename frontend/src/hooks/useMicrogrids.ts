import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/services/apiClient";
import type { MicrogridSummary } from "@/types/microgrid";

export type MicrogridsStatus = "loading" | "success" | "error";

export interface MicrogridsState {
  status: MicrogridsStatus;
  microgrids: MicrogridSummary[];
  errorMessage: string | null;
  seeding: boolean;
  refresh: () => void;
  seedDemo: () => Promise<MicrogridSummary | null>;
}

/**
 * Lists existing microgrids (read-only, GET /api/microgrids) and exposes
 * an explicit action to seed the documented demo microgrid
 * (POST /api/demo/seed). Seeding only ever happens when the user clicks
 * the "Load demo microgrid" button in the UI — never automatically.
 */
export function useMicrogrids(): MicrogridsState {
  const [status, setStatus] = useState<MicrogridsStatus>("loading");
  const [microgrids, setMicrogrids] = useState<MicrogridSummary[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);

  const refresh = useCallback(() => {
    setStatus("loading");
    apiClient
      .listMicrogrids()
      .then((data) => {
        setMicrogrids(data);
        setStatus("success");
        setErrorMessage(null);
      })
      .catch((err: unknown) => {
        setStatus("error");
        setErrorMessage(err instanceof Error ? err.message : "Failed to list microgrids.");
      });
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const seedDemo = useCallback(async (): Promise<MicrogridSummary | null> => {
    setSeeding(true);
    try {
      const result = await apiClient.seedDemoMicrogrid();
      refresh();
      return result.microgrid;
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to seed demo microgrid.");
      return null;
    } finally {
      setSeeding(false);
    }
  }, [refresh]);

  return { status, microgrids, errorMessage, seeding, refresh, seedDemo };
}
