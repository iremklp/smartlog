import type { ApiErrorShape } from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly detail?: string;

  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_REQUEST_TIMEOUT_MS ?? 20000);

function readStringProperty(value: unknown, property: string): string | undefined {
  if (typeof value !== "object" || value === null) {
    return undefined;
  }
  const candidate = (value as Record<string, unknown>)[property];
  return typeof candidate === "string" && candidate.trim() ? candidate.trim() : undefined;
}

function readErrorDetail(payload: ApiErrorShape): string | undefined {
  if (typeof payload.detail === "string") {
    const detail = payload.detail.trim();
    return detail || undefined;
  }

  if (Array.isArray(payload.detail)) {
    const messages = payload.detail
      .map(
        (item) =>
          readStringProperty(item, "message") ??
          readStringProperty(item, "msg") ??
          readStringProperty(item, "code")
      )
      .filter((message): message is string => message !== undefined);
    if (messages.length > 0) {
      return messages.join("; ");
    }
  }

  return (
    readStringProperty(payload.detail, "message") ??
    readStringProperty(payload.detail, "code") ??
    readStringProperty(payload.error, "message") ??
    readStringProperty(payload.error, "code")
  );
}

function buildUrl(path: string): string {
  const rawBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const base = rawBase.endsWith("/") ? rawBase.slice(0, -1) : rawBase;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalizedPath}`;
}

async function withTimeout<T>(promise: Promise<T>, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  let timer: number | undefined;
  const timeoutPromise = new Promise<T>((_, reject) => {
    timer = window.setTimeout(() => {
      reject(new ApiError(408, "Request timed out"));
    }, timeoutMs);
  });
  try {
    return await Promise.race([promise, timeoutPromise]);
  } finally {
    if (timer !== undefined) {
      window.clearTimeout(timer);
    }
  }
}

export async function requestJson<TResponse>(
  path: string,
  init: RequestInit = {},
  signal?: AbortSignal
): Promise<TResponse> {
  const headers = new Headers(init.headers ?? {});
  if (!headers.has("Content-Type") && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await withTimeout(
    fetch(buildUrl(path), {
      ...init,
      headers,
      signal
    })
  );

  if (!response.ok) {
    const fallback = `Request failed with status ${response.status}`;
    let detail: string | undefined;
    try {
      const payload = (await response.json()) as ApiErrorShape;
      detail = readErrorDetail(payload);
    } catch {
      detail = undefined;
    }
    throw new ApiError(response.status, detail ?? fallback, detail);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}
