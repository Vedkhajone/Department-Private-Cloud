/**
 * Small fetch wrapper for the DECP API.
 *
 * All requests go through relative "/api/..." paths -- NGINX proxies
 * those to the backend, so the browser never talks to FastAPI directly.
 */

const API_BASE = "/api";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    return JSON.stringify(body.detail ?? body);
  } catch {
    return res.statusText;
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }

  // 204 No Content etc. -- nothing to parse.
  if (res.status === 204) return undefined as T;

  return (await res.json()) as T;
}
