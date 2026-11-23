export type ApiErrorCode = "network" | "not_found" | "validation" | "auth";

export interface Violation {
  code: string;
  reason: string;
  detail: string | null;
}

export class ApiError extends Error {
  code: ApiErrorCode;
  /** Machine code from the server's `{error, code}` body, when it sent one. */
  serverCode?: string;
  violations: Violation[];
  status?: number;

  constructor(code: ApiErrorCode, message: string, extra: { serverCode?: string; violations?: Violation[]; status?: number } = {}) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.serverCode = extra.serverCode;
    this.violations = extra.violations ?? [];
    this.status = extra.status;
  }
}

const BASE = (import.meta.env.VITE_API_URL ?? "/api/v1").replace(/\/$/, "");

/** Absolute URL for an API path; relative bases resolve against the page origin. */
export function apiUrl(path: string) {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return new URL(`${BASE}${normalized}`, globalThis.location?.origin ?? "http://localhost").toString();
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  /** Sent as JSON with a JSON content type. */
  json?: unknown;
  /** Sent as-is; the browser sets the multipart boundary itself. */
  form?: FormData;
}

/** One request helper for the API: cookies included, JSON in and out, errors mapped to ApiError. */
export async function apiRequest<T>(path: string, { json, form, headers, ...init }: RequestOptions = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(apiUrl(path), {
      ...init,
      credentials: "include",
      headers: { Accept: "application/json", ...(json !== undefined ? { "Content-Type": "application/json" } : {}), ...headers },
      body: json !== undefined ? JSON.stringify(json) : form,
    });
  } catch {
    throw new ApiError("network", "Could not reach the server. Check your connection and try again.");
  }
  if (res.ok) return (await res.json()) as T;
  const body = (await res.json().catch(() => null)) as { error?: string; code?: string; violations?: Violation[] } | null;
  const extra = { serverCode: body?.code, violations: body?.violations, status: res.status };
  if (res.status === 401) throw new ApiError("auth", "Your session ended. Sign in again.", extra);
  if (res.status === 404) throw new ApiError("not_found", body?.error ?? "Not found.", extra);
  if (res.status >= 400 && res.status < 500) throw new ApiError("validation", body?.error ?? "Some information is invalid.", extra);
  throw new ApiError("network", body?.error ?? "The server had a problem. Try again in a moment.", extra);
}
