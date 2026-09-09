import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, request } from "../../lib/api/http";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("request", () => {
  it("preserves FastAPI status and validation messages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        headers: { get: () => "application/json" },
        json: () => Promise.resolve({ detail: [{ msg: "Champ invalide" }] }),
      }),
    );

    await expect(request("/api/projects")).rejects.toMatchObject({
      name: "ApiError",
      status: 422,
      message: "Champ invalide",
    });
  });

  it("normalizes local network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    await expect(request("/api/projects")).rejects.toEqual(
      new ApiError("Impossible de joindre le serveur local.", 0, expect.any(Error)),
    );
  });
});
