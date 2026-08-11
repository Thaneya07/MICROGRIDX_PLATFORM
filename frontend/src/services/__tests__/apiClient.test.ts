import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient, ApiError } from "@/services/apiClient";

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
