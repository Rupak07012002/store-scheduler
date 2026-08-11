const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const ACCESS_TOKEN_KEY = "scheduler_access_token";
const REFRESH_TOKEN_KEY = "scheduler_refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function refreshAccessToken(): Promise<boolean> {
  const refresh = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refresh) return false;
  const res = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) return false;
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return true;
}

export async function apiRequest<T>(
  path: string,
  options: { method?: string; body?: unknown; retry?: boolean } = {},
): Promise<T> {
  const { method = "GET", body, retry = true } = options;
  const token = getAccessToken();

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiRequest<T>(path, { method, body, retry: false });
    }
    clearTokens();
    window.location.href = "/login";
    throw new ApiError(401, "Session expired");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      // response had no JSON body
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}
