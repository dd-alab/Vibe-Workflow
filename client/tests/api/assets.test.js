import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  assetContentUrl,
  assetThumbnailUrl,
  deleteReference,
  uploadReference,
} from "../../lib/api/assets";
import { request, uploadRequest } from "../../lib/api/http";

vi.mock("../../lib/api/http", () => ({
  request: vi.fn(),
  uploadRequest: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("asset API", () => {
  it("sends multipart fields through the centralized upload helper", () => {
    const file = new File(["image"], "portrait.png", { type: "image/png" });
    const onProgress = vi.fn();

    uploadReference("project id", "character/id", file, {
      expectedRevision: 7,
      onProgress,
    });

    const [path, formData, options] = uploadRequest.mock.calls[0];
    expect(path).toBe(
      "/api/projects/project%20id/characters/character%2Fid/references",
    );
    expect(formData.get("file")).toBe(file);
    expect(formData.get("expected_revision")).toBe("7");
    expect(options.onProgress).toBe(onProgress);
  });

  it("centralizes delete and serving URLs by asset id", () => {
    deleteReference("project", "character", "asset/id", {
      expectedRevision: 4,
    });

    expect(request).toHaveBeenCalledWith(
      "/api/projects/project/characters/character/references/asset%2Fid?expected_revision=4",
      { method: "DELETE" },
    );
    expect(assetThumbnailUrl("asset/id")).toBe(
      "/api/assets/asset%2Fid/thumbnail",
    );
    expect(assetContentUrl("asset/id")).toBe(
      "/api/assets/asset%2Fid/content",
    );
  });
});
