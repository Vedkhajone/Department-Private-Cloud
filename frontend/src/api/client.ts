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
  // Let the browser set Content-Type (with the multipart boundary)
  // itself for FormData bodies -- only default to JSON otherwise.
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }

  // 204 No Content etc. -- nothing to parse.
  if (res.status === 204) return undefined as T;

  return (await res.json()) as T;
}

/**
 * Fetches a file that requires authentication and triggers a normal
 * browser "Save As" download for it, preserving the filename the
 * server sent via Content-Disposition.
 */
export async function downloadFile(
  path: string,
  token: string | null,
  fallbackFilename: string
): Promise<void> {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { headers });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }

  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : fallbackFilename;

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
