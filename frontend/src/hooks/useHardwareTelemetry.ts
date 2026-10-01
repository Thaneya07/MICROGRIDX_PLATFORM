import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/services/apiClient";

const ESP32_DEVICE_ID =
  import.meta.env.VITE_ESP32_DEVICE_ID?.trim() || null;

export interface HardwareTelemetry {
  device_id: string;
  recorded_at: string;
  temperature_c: number | null;
  humidity_percent: number | null;
  voltage_v: number;
  current_a: number;
  power_w: number;
  status: string;
  source: string;
}

interface HardwareTelemetryState {
  data: HardwareTelemetry | null;
  loading: boolean;
  error: string | null;
}

export function useHardwareTelemetry(
  refreshInterval = 3000
): HardwareTelemetryState {
  const [data, setData] =
    useState<HardwareTelemetry | null>(null);

  const [loading, setLoading] =
    useState(Boolean(ESP32_DEVICE_ID));

  const [error, setError] =
    useState<string | null>(null);

  const fetchTelemetry = useCallback(async () => {
    /*
     * No registered physical ESP32 device has been configured.
     * Do not repeatedly call a stale UUID.
     */
    if (!ESP32_DEVICE_ID) {
      setLoading(false);
      setData(null);
      setError(null);
      return;
    }

    try {
      setLoading(true);

      const telemetry =
        await apiClient.getHardwareTelemetry(
          ESP32_DEVICE_ID
        );

      setData(telemetry);
      setError(null);

    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to fetch ESP32 telemetry.";

      setData(null);
      setError(message);

    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchTelemetry();

    /*
     * Only poll when a physical ESP32 device ID
     * has actually been configured.
     */
    if (!ESP32_DEVICE_ID) {
      return;
    }

    const interval =
      window.setInterval(
        () => {
          void fetchTelemetry();
        },
        refreshInterval
      );

    return () => {
      window.clearInterval(interval);
    };
  }, [
    fetchTelemetry,
    refreshInterval,
  ]);

  return {
    data,
    loading,
    error,
  };
}