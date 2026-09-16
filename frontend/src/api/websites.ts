import { apiRequest } from "./client";

export type WebsiteType = "static" | "dynamic";
export type WebsiteFramework = "html" | "react" | "flask" | "fastapi" | "node";
export type WebsiteStatus = "pending" | "building" | "online" | "stopped" | "failed" | "deleting";

export interface Website {
  id: string;
  name: string;
  slug: string;
  type: WebsiteType;
  framework: WebsiteFramework;
  status: WebsiteStatus;
  public_url: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export function listWebsites(token: string): Promise<Website[]> {
  return apiRequest<Website[]>("/websites", { method: "GET" }, token);
}

export function getWebsite(token: string, id: string): Promise<Website> {
  return apiRequest<Website>(`/websites/${id}`, { method: "GET" }, token);
}

export function deployWebsite(token: string, name: string, zip: File): Promise<Website> {
  const formData = new FormData();
  formData.append("name", name);
  formData.append("upload", zip);
  return apiRequest<Website>("/websites", { method: "POST", body: formData }, token);
}

export function deleteWebsite(token: string, id: string): Promise<void> {
  return apiRequest<void>(`/websites/${id}`, { method: "DELETE" }, token);
}

export function startWebsite(token: string, id: string): Promise<Website> {
  return apiRequest<Website>(`/websites/${id}/start`, { method: "POST" }, token);
}

export function stopWebsite(token: string, id: string): Promise<Website> {
  return apiRequest<Website>(`/websites/${id}/stop`, { method: "POST" }, token);
}

export function restartWebsite(token: string, id: string): Promise<Website> {
  return apiRequest<Website>(`/websites/${id}/restart`, { method: "POST" }, token);
}

export function getWebsiteLogs(token: string, id: string): Promise<{ logs: string }> {
  return apiRequest<{ logs: string }>(`/websites/${id}/logs`, { method: "GET" }, token);
}
