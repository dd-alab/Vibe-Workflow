import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, request, uploadRequest } from "../../lib/api/http";

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
        text: () => Promise.resolve('{"detail":[{"msg":"Champ invalide"}]}'),
      }),
    );

    await expect(request("/api/projects")).rejects.toMatchObject({
      name: "ApiError",
      status: 422,
      message: "Champ invalide",
    });
  });

  it("accepts empty success responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 204,
        headers: { get: () => "application/json" },
        text: () => Promise.resolve(""),
      }),
    );

    await expect(request("/api/projects/project-uuid", { method: "DELETE" }))
      .resolves.toBeNull();
  });

  it("normalizes local network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    await expect(request("/api/projects")).rejects.toEqual(
      new ApiError("Impossible de joindre le serveur local.", 0, expect.any(Error)),
    );
  });
});

describe("uploadRequest", () => {
  it("reports upload progress without setting a multipart content type", async () => {
    const requests = [];
    class FakeXMLHttpRequest {
      constructor() {
        this.headers = {};
        this.upload = {};
        requests.push(this);
      }

      open(method, path) {
        this.method = method;
        this.path = path;
      }

      setRequestHeader(name, value) {
        this.headers[name] = value;
      }

      send(body) {
        this.body = body;
      }
    }
    vi.stubGlobal("XMLHttpRequest", FakeXMLHttpRequest);
    const onProgress = vi.fn();
    const formData = new FormData();

    const result = uploadRequest("/api/upload", formData, { onProgress });
    const xhr = requests[0];
    xhr.upload.onprogress({ lengthComputable: true, loaded: 5, total: 10 });
    xhr.status = 201;
    xhr.responseText = '{"revision":1}';
    xhr.onload();

    await expect(result).resolves.toEqual({ revision: 1 });
    expect(onProgress).toHaveBeenCalledWith(50);
    expect(xhr.headers.Accept).toBe("application/json");
    expect(xhr.headers["Content-Type"]).toBeUndefined();
    expect(xhr.body).toBe(formData);
  });

  it("rejects an already aborted upload without opening a request", async () => {
    const controller = new AbortController();
    controller.abort();

    await expect(
      uploadRequest("/api/upload", new FormData(), {
        signal: controller.signal,
      }),
    ).rejects.toMatchObject({ name: "AbortError" });
  });
});
