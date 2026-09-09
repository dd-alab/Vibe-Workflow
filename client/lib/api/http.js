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
