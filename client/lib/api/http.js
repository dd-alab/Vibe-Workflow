export class ApiError extends Error {
  constructor(message, status = 0, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function detailMessage(detail) {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg)
      .filter(Boolean)
      .join(" ");
  }
  return "La requete locale a echoue.";
}

function parseJson(value) {
  if (!value) {
    return null;
  }
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

export function uploadRequest(path, formData, options = {}) {
  return new Promise((resolve, reject) => {
    if (options.signal?.aborted) {
      reject(new DOMException("Import annule", "AbortError"));
      return;
    }
    const xhr = new XMLHttpRequest();
    const { onProgress, signal } = options;
    let settled = false;

    function cleanup() {
      signal?.removeEventListener("abort", handleSignalAbort);
    }

    function settle(callback, value) {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      callback(value);
    }

    function handleSignalAbort() {
      xhr.abort();
    }

    xhr.open("POST", path);
    xhr.setRequestHeader("Accept", "application/json");
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && event.total > 0) {
        onProgress?.(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      const payload = parseJson(xhr.responseText);
      if (xhr.status >= 200 && xhr.status < 300) {
        settle(resolve, payload);
        return;
      }
      settle(
        reject,
        new ApiError(
          detailMessage(payload?.detail),
          xhr.status,
          payload?.detail ?? null,
        ),
      );
    };
    xhr.onerror = () => {
      settle(
        reject,
        new ApiError("Impossible de joindre le serveur local.", 0),
      );
    };
    xhr.onabort = () => {
      settle(reject, new DOMException("Import annule", "AbortError"));
    };
    signal?.addEventListener("abort", handleSignalAbort, { once: true });
    xhr.send(formData);
  });
}

export async function request(path, options = {}) {
  const method = options.method ?? "GET";
  const hasBody = options.body !== undefined;
  let response;

  try {
    response = await fetch(path, {
      ...options,
      method,
      cache: method === "GET" ? "no-store" : options.cache,
      headers: {
        Accept: "application/json",
        ...(hasBody ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
      body: hasBody ? JSON.stringify(options.body) : undefined,
    });
  } catch (error) {
    throw new ApiError(
      "Impossible de joindre le serveur local.",
      0,
      error,
    );
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    throw new ApiError(
      detailMessage(payload?.detail),
      response.status,
      payload?.detail ?? null,
    );
  }

  return payload;
}
