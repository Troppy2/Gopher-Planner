export type ApiErrorCode =
  | "network"
  | "unauthorized"
  | "not_found"
  | "validation"
  | "auth"
  | "server";

export class ApiError extends Error {
  code: ApiErrorCode;

  constructor(code: ApiErrorCode, message: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
  }
}

const BASE = (import.meta.env.VITE_API_URL ?? "/api/v1").replace(/\/$/, "");

/** Fetch wrapper for the real API. */
export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  let res: Response;

  try {
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;

    res = await fetch(`${BASE}${normalizedPath}`, {
      ...init,
      credentials: init.credentials ?? "include",
      headers: {
        "Content-Type": "application/json",
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError("network", "Could not reach the server.");
  }

  if (res.status === 401) {
    throw new ApiError("unauthorized", "Your session ended. Sign in again.");
  }

  if (res.status === 404) {
    throw new ApiError("not_found", "Not found.");
  }

  if (res.status === 422) {
    throw new ApiError("validation", "Some fields are invalid.");
  }

  if (!res.ok) {
    throw new ApiError("server", "The server returned an error.");
  }

  return (await res.json()) as T;
}
