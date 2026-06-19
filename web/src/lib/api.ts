// Browser API client for the backend. The access token lives in memory; on a 401 we
// transparently refresh it via the same-origin BFF route (/api/auth/refresh) and retry once.

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const res = await fetch("/api/auth/refresh", { method: "POST" });
  if (!res.ok) {
    setAccessToken(null);
    return null;
  }
  const data = (await res.json()) as { access_token: string };
  setAccessToken(data.access_token);
  return data.access_token;
}

function withAuth(init: RequestInit, token: string | null): RequestInit {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return { ...init, headers };
}

/** Call the backend API with auth + one transparent token refresh on 401. */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res = await fetch(`${API_BASE}${path}`, withAuth(init, accessToken));
  if (res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      res = await fetch(`${API_BASE}${path}`, withAuth(init, refreshed));
    }
  }

  const text = await res.text();
  const data: unknown = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const error = (data as { error?: { code?: string; message?: string; details?: unknown } } | null)
      ?.error;
    throw new ApiError(
      res.status,
      error?.code ?? "error",
      error?.message ?? res.statusText,
      error?.details,
    );
  }
  return data as T;
}

export function apiJson<T>(path: string, method: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method,
    headers: body !== undefined ? { "content-type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

/** Call a same-origin BFF auth route (/api/auth/*). Returns the fresh access token info. */
export async function postAuth(
  path: string,
  body: Record<string, unknown>,
): Promise<{ access_token: string; expires_in: number }> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const error = (data as { error?: { code?: string; message?: string } } | null)?.error;
    throw new ApiError(res.status, error?.code ?? "auth_error", error?.message ?? "Ошибка входа");
  }
  return data as { access_token: string; expires_in: number };
}
