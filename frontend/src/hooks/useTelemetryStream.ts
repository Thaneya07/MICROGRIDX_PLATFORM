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
  reconnectAttempt: number;
  reconnect: () => void;
}

const CONNECT_TIMEOUT_MS = 4000;
const FALLBACK_POLL_INTERVAL_MS = 4000;
const STREAM_TICK_INTERVAL_SECONDS = 3;
const RECONNECT_BASE_DELAY_MS = 5000;
const RECONNECT_MAX_DELAY_MS = 30000;
const MAX_RECONNECT_ATTEMPTS = 5;

/**
 * Connects to the live telemetry WebSocket for a microgrid.
 *
 * - If the socket cannot be established within CONNECT_TIMEOUT_MS, or
 *   drops after connecting, falls back to polling the REST snapshot
 *   endpoint on FALLBACK_POLL_INTERVAL_MS, so the 3D scene always has a
 *   way to receive data.
 * - While on fallback, automatically retries the WebSocket in the
 *   background using bounded exponential backoff (base 5s, doubling, capped
 *   at 30s, up to MAX_RECONNECT_ATTEMPTS) — never retries forever.
 * - Never throws into the caller: malformed messages, connection errors,
 *   and fallback fetch failures are all captured into `errorMessage`.
 */
export function useTelemetryStream(microgridId: string | null): TelemetryStreamState {
  const [status, setStatus] = useState<TelemetryStreamStatus>("idle");
  const [snapshot, setSnapshot] = useState<MicrogridSnapshot | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [usingFallback, setUsingFallback] = useState(false);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [generation, setGeneration] = useState(0); // bump to force a (re)connect attempt

  const connectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const backoffTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);
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
    if (backoffTimeoutRef.current) {
      clearTimeout(backoffTimeoutRef.current);
      backoffTimeoutRef.current = null;
    }
  }, []);

  const scheduleBackoffRetry = useCallback(() => {
    if (attemptRef.current >= MAX_RECONNECT_ATTEMPTS) return;
    const delay = Math.min(RECONNECT_MAX_DELAY_MS, RECONNECT_BASE_DELAY_MS * 2 ** attemptRef.current);
    attemptRef.current += 1;
    setReconnectAttempt(attemptRef.current);
    backoffTimeoutRef.current = setTimeout(() => {
      if (unmountedRef.current) return;
      setGeneration((g) => g + 1);
    }, delay);
  }, []);

  const startFallbackPolling = useCallback(
    (id: string) => {
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
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = setInterval(poll, FALLBACK_POLL_INTERVAL_MS);

      scheduleBackoffRetry();
    },
    [scheduleBackoffRetry]
  );

  useEffect(() => {
    unmountedRef.current = false;

    if (!microgridId) {
      setStatus("idle");
      return;
    }

    setStatus((prev) => (prev === "fallback_polling" || prev === "reconnecting" ? "reconnecting" : "connecting"));
    setErrorMessage(null);

    const url = getTelemetryStreamUrl(microgridId, STREAM_TICK_INTERVAL_SECONDS);
    let socket: WebSocket;
    let terminalHandled = false; // guards against the connect-timeout and its own close() both triggering fallback
    try {
      socket = new WebSocket(url);
    } catch {
      startFallbackPolling(microgridId);
      return () => clearTimers();
    }

    connectTimeoutRef.current = setTimeout(() => {
      if (socket.readyState !== WebSocket.OPEN && !terminalHandled) {
        terminalHandled = true;
        socket.close();
        startFallbackPolling(microgridId);
      }
    }, CONNECT_TIMEOUT_MS);

    socket.onopen = () => {
      if (connectTimeoutRef.current) {
        clearTimeout(connectTimeoutRef.current);
        connectTimeoutRef.current = null;
      }
      // A successful connection cancels any pending fallback poll/backoff
      // retry from a previous attempt.
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      if (backoffTimeoutRef.current) {
        clearTimeout(backoffTimeoutRef.current);
        backoffTimeoutRef.current = null;
      }
      attemptRef.current = 0;
      setReconnectAttempt(0);
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
      if (unmountedRef.current || terminalHandled) return;
      terminalHandled = true;
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
    attemptRef.current = 0;
    setReconnectAttempt(0);
    setUsingFallback(false);
    setSnapshot(null);
    setErrorMessage(null);
    setGeneration((g) => g + 1);
  }, []);

  return { status, snapshot, errorMessage, usingFallback, reconnectAttempt, reconnect };
}
