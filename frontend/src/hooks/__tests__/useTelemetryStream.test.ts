import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useTelemetryStream } from "@/hooks/useTelemetryStream";
import { apiClient } from "@/services/apiClient";
import type { MicrogridSnapshot } from "@/types/telemetry";

const SAMPLE_SNAPSHOT: MicrogridSnapshot = {
  microgrid_id: "mg-1",
  name: "Test Grid",
  location: "Site A",
  status: "ACTIVE",
  server_time: "2026-06-15T12:00:00Z",
  source: "SIMULATED",
  energy_reading: null,
  devices: [],
  loads: [],
  energy_reading_error: null,
};

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static behavior: "open" | "never_open" | "throw" = "open";

  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 0;
  url: string;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    if (MockWebSocket.behavior === "throw") {
      throw new Error("Connection refused");
    }
    if (MockWebSocket.behavior === "open") {
      setTimeout(() => {
        this.readyState = 1;
        this.onopen?.();
      }, 10);
    }
  }

  send() {
    /* no-op */
  }

  close() {
    this.readyState = 3;
    this.onclose?.();
  }

  emitMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

async function tick(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe("useTelemetryStream", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.instances = [];
    MockWebSocket.behavior = "open";
    vi.stubGlobal("WebSocket", MockWebSocket as unknown as typeof WebSocket);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("stays idle when no microgridId is provided", () => {
    const { result } = renderHook(() => useTelemetryStream(null));
    expect(result.current.status).toBe("idle");
    expect(result.current.snapshot).toBeNull();
  });

  it("connects and receives a snapshot over the WebSocket", async () => {
    const { result } = renderHook(() => useTelemetryStream("mg-1"));
    expect(result.current.status).toBe("connecting");

    await tick(20);
    expect(result.current.status).toBe("connected");

    act(() => {
      MockWebSocket.instances[0].emitMessage({ type: "snapshot", ...SAMPLE_SNAPSHOT });
    });

    expect(result.current.snapshot).toEqual(SAMPLE_SNAPSHOT);
    expect(result.current.usingFallback).toBe(false);
  });

  it("surfaces a server-sent error message without crashing", async () => {
    const { result } = renderHook(() => useTelemetryStream("mg-1"));
    await tick(20);
    expect(result.current.status).toBe("connected");

    act(() => {
      MockWebSocket.instances[0].emitMessage({ type: "error", code: "NOT_FOUND", message: "Microgrid not found." });
    });

    expect(result.current.status).toBe("error");
    expect(result.current.errorMessage).toBe("Microgrid not found.");
  });

  it("handles a malformed (non-JSON) message without crashing", async () => {
    const { result } = renderHook(() => useTelemetryStream("mg-1"));
    await tick(20);
    expect(result.current.status).toBe("connected");

    act(() => {
      MockWebSocket.instances[0].onmessage?.({ data: "not valid json {{{" });
    });

    expect(result.current.errorMessage).toBe("Received a malformed telemetry message.");
  });

  it("falls back to REST polling when the socket never opens", async () => {
    MockWebSocket.behavior = "never_open";
    const snapshotSpy = vi.spyOn(apiClient, "getMicrogridSnapshot").mockResolvedValue(SAMPLE_SNAPSHOT);

    const { result } = renderHook(() => useTelemetryStream("mg-1"));
    expect(result.current.status).toBe("connecting");

    await tick(4100); // past CONNECT_TIMEOUT_MS

    expect(result.current.usingFallback).toBe(true);
    expect(result.current.status).toBe("fallback_polling");
    expect(snapshotSpy).toHaveBeenCalledWith("mg-1");
    expect(result.current.snapshot).toEqual(SAMPLE_SNAPSHOT);
  });

  it("falls back to REST polling if the socket construction throws", async () => {
    MockWebSocket.behavior = "throw";
    const snapshotSpy = vi.spyOn(apiClient, "getMicrogridSnapshot").mockResolvedValue(SAMPLE_SNAPSHOT);

    const { result } = renderHook(() => useTelemetryStream("mg-1"));
    await tick(0);

    expect(result.current.usingFallback).toBe(true);
    expect(snapshotSpy).toHaveBeenCalled();
  });

  it("falls back to REST polling after the socket closes unexpectedly", async () => {
    const { result } = renderHook(() => useTelemetryStream("mg-1"));
    await tick(20);
    expect(result.current.status).toBe("connected");

    const snapshotSpy = vi.spyOn(apiClient, "getMicrogridSnapshot").mockResolvedValue(SAMPLE_SNAPSHOT);

    act(() => {
      MockWebSocket.instances[0].close();
    });
    await tick(0);

    expect(result.current.usingFallback).toBe(true);
    expect(snapshotSpy).toHaveBeenCalled();
  });

  it("surfaces a fallback fetch error without crashing", async () => {
    MockWebSocket.behavior = "never_open";
    vi.spyOn(apiClient, "getMicrogridSnapshot").mockRejectedValue(new Error("Network unreachable"));

    const { result } = renderHook(() => useTelemetryStream("mg-1"));
    await tick(4100);

    expect(result.current.errorMessage).toBe("Network unreachable");
  });

  it("reconnect() resets state and retries", async () => {
    const { result } = renderHook(() => useTelemetryStream("mg-1"));
    await tick(20);
    expect(result.current.status).toBe("connected");

    act(() => {
      MockWebSocket.instances[0].emitMessage({ type: "snapshot", ...SAMPLE_SNAPSHOT });
    });
    expect(result.current.snapshot).not.toBeNull();

    act(() => {
      result.current.reconnect();
    });
    expect(result.current.snapshot).toBeNull();

    await tick(20);
    expect(result.current.status).toBe("connected");
  });
});
