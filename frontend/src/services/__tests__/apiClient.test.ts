import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient, ApiError, getTelemetryStreamUrl } from "@/services/apiClient";

describe("apiClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed JSON on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok", service: "microgridx-api" }),
      })
    );

    const result = await apiClient.getHealth();
    expect(result).toEqual({ status: "ok", service: "microgridx-api" });
  });

  it("throws ApiError with backend-provided message on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({
          error: { code: "SERVICE_UNAVAILABLE", message: "Database connection failed." },
        }),
      })
    );

    await expect(apiClient.getDatabaseHealth()).rejects.toMatchObject({
      message: "Database connection failed.",
      status: 503,
      code: "SERVICE_UNAVAILABLE",
    });
  });

  it("ApiError is an instance of Error", async () => {
    const err = new ApiError(500, "boom");
    expect(err).toBeInstanceOf(Error);
  });
});

describe("apiClient Step 6 additions", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("getMicrogridSnapshot calls the correct endpoint and returns parsed JSON", async () => {
    const mockSnapshot = { microgrid_id: "mg-1", source: "SIMULATED" };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => mockSnapshot });
    vi.stubGlobal("fetch", fetchMock);

    const result = await apiClient.getMicrogridSnapshot("mg-1");
    expect(result).toEqual(mockSnapshot);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/telemetry/microgrids/mg-1/snapshot"),
      expect.any(Object)
    );
  });

  it("getForecast calls the correct endpoint with query params", async () => {
    const mockForecast = { microgrid_id: "mg-1", target: "DEMAND" };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => mockForecast });
    vi.stubGlobal("fetch", fetchMock);

    await apiClient.getForecast("mg-1", "DEMAND", "2026-06-15T00:00:00Z", "2026-06-16T00:00:00Z", 30);
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/api/forecast/microgrids/mg-1");
    expect(calledUrl).toContain("target=DEMAND");
    expect(calledUrl).toContain("interval_minutes=30");
  });
});

describe("getTelemetryStreamUrl", () => {
  it("converts http(s) base URL to ws(s)", () => {
    const url = getTelemetryStreamUrl("mg-1", 5);
    expect(url.startsWith("ws://") || url.startsWith("wss://")).toBe(true);
    expect(url).toContain("/api/telemetry/microgrids/mg-1/stream");
    expect(url).toContain("interval_seconds=5");
  });
});

describe("apiClient microgrid/demo additions", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("listMicrogrids calls the correct endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    await apiClient.listMicrogrids();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/microgrids"), expect.any(Object));
  });

  it("seedDemoMicrogrid POSTs to the demo seed endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);
    await apiClient.seedDemoMicrogrid();
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/demo/seed");
    expect(options.method).toBe("POST");
  });
});
