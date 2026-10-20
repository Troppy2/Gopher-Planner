import type { AuthUser } from "./session.store";

interface GoogleLoginResponse {
  user: AuthUser;
  expires_in: number;
}

interface SessionResponse {
  user: AuthUser;
}

function getApiUrl(): string {
  return (import.meta.env.VITE_API_URL ?? "/api/v1").replace(/\/$/, "");
}

async function getErrorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  const data: unknown = await response.json().catch(() => null);

  if (
    typeof data === "object" &&
    data !== null &&
    "error" in data &&
    typeof data.error === "string"
  ) {
    return data.error;
  }

  return fallback;
}

export async function loginWithGoogle(
  credential: string,
): Promise<GoogleLoginResponse> {
  const response = await fetch(`${getApiUrl()}/auth/google`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ credential }),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Google sign-in failed"));
  }

  return (await response.json()) as GoogleLoginResponse;
}

export async function getCurrentSession(): Promise<AuthUser> {
  const response = await fetch(`${getApiUrl()}/auth/session`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("No valid session");
  }

  const data = (await response.json()) as SessionResponse;

  return data.user;
}

export async function logoutFromServer(): Promise<void> {
  const response = await fetch(`${getApiUrl()}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Unable to sign out on the server");
  }
}
