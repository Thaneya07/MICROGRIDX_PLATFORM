import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useMicrogrids } from "@/hooks/useMicrogrids";
import { apiClient } from "@/services/apiClient";
import type { DemoSeedResponse, MicrogridSummary } from "@/types/microgrid";

const SAMPLE_LIST: MicrogridSummary[] = [
  { id: "mg-1", name: "Demo Site", location: "Demo (simulated data)", status: "ACTIVE", created_at: "2026-06-15T00:00:00Z" },
];

const SAMPLE_SEED_RESPONSE: DemoSeedResponse = {
  microgrid: SAMPLE_LIST[0],
  already_existed: false,
  readings_backfilled: 240,
  message: "Created demo microgrid.",
};

describe("useMicrogrids", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads the microgrid list on mount", async () => {
    vi.spyOn(apiClient, "listMicrogrids").mockResolvedValue(SAMPLE_LIST);
    const { result } = renderHook(() => useMicrogrids());
    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.microgrids).toEqual(SAMPLE_LIST);
  });

  it("surfaces a list error", async () => {
    vi.spyOn(apiClient, "listMicrogrids").mockRejectedValue(new Error("Network unreachable"));
    const { result } = renderHook(() => useMicrogrids());
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.errorMessage).toBe("Network unreachable");
  });

  it("seedDemo calls the seed endpoint, refreshes the list, and returns the microgrid", async () => {
    vi.spyOn(apiClient, "listMicrogrids").mockResolvedValue([]);
    const seedSpy = vi.spyOn(apiClient, "seedDemoMicrogrid").mockResolvedValue(SAMPLE_SEED_RESPONSE);

    const { result } = renderHook(() => useMicrogrids());
    await waitFor(() => expect(result.current.status).toBe("success"));

    let returned: MicrogridSummary | null = null;
    await act(async () => {
      returned = await result.current.seedDemo();
    });

    expect(seedSpy).toHaveBeenCalled();
    expect(returned).toEqual(SAMPLE_LIST[0]);
    expect(result.current.seeding).toBe(false);
  });

  it("seedDemo surfaces an error and returns null on failure", async () => {
    vi.spyOn(apiClient, "listMicrogrids").mockResolvedValue([]);
    vi.spyOn(apiClient, "seedDemoMicrogrid").mockRejectedValue(new Error("Seed failed"));

    const { result } = renderHook(() => useMicrogrids());
    await waitFor(() => expect(result.current.status).toBe("success"));

    let returned: MicrogridSummary | null = SAMPLE_LIST[0];
    await act(async () => {
      returned = await result.current.seedDemo();
    });

    expect(returned).toBeNull();
    expect(result.current.errorMessage).toBe("Seed failed");
  });
});
