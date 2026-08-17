import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient, getTelemetryStreamUrl } from "@/services/apiClient";
import type { MicrogridSnapshot, StreamMessage } from "@/types/telemetry";

export type TelemetryStreamStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "fallback_polling"
  | "disconnected"
  | "error";

export interface TelemetryStreamState {
  status: TelemetryStreamStatus;
  snapshot: MicrogridSnapshot | null;
  errorMessage: string | null;
  usingFallback: boolean;
  reconnect: () => void;
}

const CONNECT_TIMEOUT_MS = 4000;
const FALLBACK_POLL_INTERVAL_MS = 4000;
const STREAM_TICK_INTERVAL_SECONDS = 3;

/**
 * Connects to the live telemetry WebSocket for a microgrid. If the socket
 * cannot be established within CONNECT_TIMEOUT_MS, or drops after
 * connecting, this hook falls back to polling the REST snapshot endpoint
 * (GET /api/telemetry/microgrids/{id}/snapshot) on FALLBACK_POLL_INTERVAL_MS,
 * so the 3D scene always has a way to receive data.
 */
export function useTelemetryStream(microgridId: string | null): TelemetryStreamState {
  const [status, setStatus] = useState<TelemetryStreamStatus>("idle");
  const [snapshot, setSnapshot] = useState<MicrogridSnapshot | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [usingFallback, setUsingFallback] = useState(false);
  const [generation, setGeneration] = useState(0); // bump to force a reconnect attempt

  const connectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const unmountedRef = useRef(false);

  const clearTimers = useCallback(() => {
    if (connectTimeoutRef.current) {
      clearTimeout(connectTimeoutRef.current);
      connectTimeoutRef.current = null;
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const startFallbackPolling = useCallback((id: string) => {
    setUsingFallback(true);
    setStatus("fallback_polling");

    const poll = () => {
      apiClient
        .getMicrogridSnapshot(id)
        .then((data) => {
          if (unmountedRef.current) return;
          setSnapshot(data);
          setErrorMessage(null);
        })
        .catch((err: unknown) => {
          if (unmountedRef.current) return;
          setErrorMessage(err instanceof Error ? err.message : "Failed to fetch telemetry snapshot.");
        });
    };

    poll();
    pollIntervalRef.current = setInterval(poll, FALLBACK_POLL_INTERVAL_MS);
  }, []);

  useEffect(() => {
    unmountedRef.current = false;

    if (!microgridId) {
      setStatus("idle");
      return;
    }

    setStatus("connecting");
    setErrorMessage(null);

    const url = getTelemetryStreamUrl(microgridId, STREAM_TICK_INTERVAL_SECONDS);
    let socket: WebSocket;
    let usingFallbackLocal = false;
    try {
      socket = new WebSocket(url);
    } catch {
      startFallbackPolling(microgridId);
      return () => clearTimers();
    }

    connectTimeoutRef.current = setTimeout(() => {
      if (socket.readyState !== WebSocket.OPEN) {
        usingFallbackLocal = true;
        socket.close();
        startFallbackPolling(microgridId);
      }
    }, CONNECT_TIMEOUT_MS);

    socket.onopen = () => {
      if (connectTimeoutRef.current) {
        clearTimeout(connectTimeoutRef.current);
        connectTimeoutRef.current = null;
      }
      setUsingFallback(false);
      setStatus("connected");
      setErrorMessage(null);
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as StreamMessage;
        if (message.type === "snapshot") {
          const { type, ...rest } = message;
          setSnapshot(rest);
          setErrorMessage(null);
        } else if (message.type === "error") {
          setErrorMessage(message.message);
          setStatus("error");
        }
      } catch {
        setErrorMessage("Received a malformed telemetry message.");
      }
    };

    socket.onclose = () => {
      if (unmountedRef.current || usingFallbackLocal) return;
      setStatus("reconnecting");
      startFallbackPolling(microgridId);
    };

    socket.onerror = () => {
      // onclose fires next and triggers fallback; nothing else to do here.
    };

    return () => {
      unmountedRef.current = true;
      clearTimers();
      socket.onopen = null;
      socket.onmessage = null;
      socket.onclose = null;
      socket.onerror = null;
      socket.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [microgridId, generation]);

  const reconnect = useCallback(() => {
    setUsingFallback(false);
    setSnapshot(null);
    setErrorMessage(null);
    setGeneration((g) => g + 1);
  }, []);

  return { status, snapshot, errorMessage, usingFallback, reconnect };
}
