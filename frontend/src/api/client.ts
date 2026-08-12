import type { ErrorResponse } from "./types";

const API_PREFIX = "/api";

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function loginPath(): string {
  return window.location.pathname.startsWith("/v2") ? "/v2/login" : "/login";
}

function redirectToLogin(): void {
  const target = loginPath();
  if (window.location.pathname !== target) {
    window.location.assign(target);
  }
}

function errorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") {
    return fallback;
  }
  const error = body as ErrorResponse;
  if (typeof error.detail === "string") {
    return error.detail;
  }
  if (typeof error.message === "string") {
    return error.message;
  }
  if (Array.isArray(error.detail)) {
    return error.detail.map((item) => item.msg).filter(Boolean).join("; ") || fallback;
  }
  return fallback;
}

export async function api<TResponse>(
  method: string,
  path: string,
  body?: unknown,
  init: RequestInit = {},
): Promise<TResponse> {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_PREFIX}${normalized}`, {
    ...init,
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 401 && normalized !== "/auth/login") {
    redirectToLogin();
  }

  if (response.status === 204) {
    return null as TResponse;
  }

  const responseBody: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      errorMessage(responseBody, `${response.status} ${response.statusText}`.trim()),
      response.status,
      responseBody,
    );
  }

  return responseBody as TResponse;
}

export const apiClient = {
  get: <TResponse>(path: string, init?: RequestInit) => api<TResponse>("GET", path, undefined, init),
  post: <TResponse>(path: string, body?: unknown, init?: RequestInit) =>
    api<TResponse>("POST", path, body, init),
  put: <TResponse>(path: string, body?: unknown, init?: RequestInit) =>
    api<TResponse>("PUT", path, body, init),
  patch: <TResponse>(path: string, body?: unknown, init?: RequestInit) =>
    api<TResponse>("PATCH", path, body, init),
  delete: <TResponse>(path: string, body?: unknown, init?: RequestInit) =>
    api<TResponse>("DELETE", path, body, init),
};
