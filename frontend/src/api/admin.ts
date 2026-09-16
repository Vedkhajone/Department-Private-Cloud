import { apiRequest } from "./client";
import type { UserRole } from "./auth";
import type { Website, WebsiteFramework, WebsiteStatus, WebsiteType } from "./websites";

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------

export interface ServiceStatus {
  name: string;
  status: "healthy" | "unavailable";
  detail: string | null;
}

export interface AdminOverview {
  total_users: number;
  new_users_this_month: number;
  storage_used_bytes: number;
  storage_capacity_bytes: number;
  storage_percent: number;
  websites_total: number;
  websites_static: number;
  websites_dynamic: number;
  services_online: number;
  services_total: number;
  services: ServiceStatus[];
}

export function getOverview(token: string): Promise<AdminOverview> {
  return apiRequest<AdminOverview>("/admin/overview", { method: "GET" }, token);
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export interface AdminUserSummary {
  id: number;
  name: string;
  email: string;
  roll_number: string | null;
  role: UserRole;
  is_active: boolean;
  storage_used_bytes: number;
  storage_limit_bytes: number;
  website_count: number;
  created_at: string;
}

export interface AdminUserListResponse {
  items: AdminUserSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminWebsiteSummary {
  id: string;
  name: string;
  slug: string;
  type: WebsiteType;
  framework: WebsiteFramework;
  status: WebsiteStatus;
  public_url: string | null;
  created_at: string;
}

export interface AdminUserDetail {
  id: number;
  name: string;
  email: string;
  roll_number: string | null;
  role: UserRole;
  is_active: boolean;
  storage_used_bytes: number;
  storage_limit_bytes: number;
  file_count: number;
  folder_count: number;
  websites: AdminWebsiteSummary[];
  created_at: string;
}

export function listUsers(
  token: string,
  search: string,
  page: number,
  pageSize = 25
): Promise<AdminUserListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (search) params.set("search", search);
  return apiRequest<AdminUserListResponse>(`/admin/users?${params}`, { method: "GET" }, token);
}

export function getUserDetail(token: string, userId: number): Promise<AdminUserDetail> {
  return apiRequest<AdminUserDetail>(`/admin/users/${userId}`, { method: "GET" }, token);
}

export function changeUserRole(token: string, userId: number, role: UserRole): Promise<AdminUserDetail> {
  return apiRequest<AdminUserDetail>(
    `/admin/users/${userId}/role`,
    { method: "PATCH", body: JSON.stringify({ role }) },
    token
  );
}

export function changeUserActive(
  token: string,
  userId: number,
  isActive: boolean
): Promise<AdminUserDetail> {
  return apiRequest<AdminUserDetail>(
    `/admin/users/${userId}/active`,
    { method: "PATCH", body: JSON.stringify({ is_active: isActive }) },
    token
  );
}

// ---------------------------------------------------------------------------
// Storage
// ---------------------------------------------------------------------------

export interface StorageTopUser {
  user_id: number;
  name: string;
  email: string;
  storage_used_bytes: number;
}

export interface StorageOverview {
  capacity_bytes: number;
  used_bytes: number;
  available_bytes: number;
  used_percent: number;
  health: "normal" | "warning" | "critical";
  warning_threshold_percent: number;
  critical_threshold_percent: number;
  file_count: number;
  folder_count: number;
  user_count: number;
  top_users: StorageTopUser[];
}

export function getStorageOverview(token: string): Promise<StorageOverview> {
  return apiRequest<StorageOverview>("/admin/storage", { method: "GET" }, token);
}

// ---------------------------------------------------------------------------
// Websites (admin)
// ---------------------------------------------------------------------------

export interface AdminWebsite extends Website {
  owner_id: number;
  owner_name: string;
  owner_email: string;
}

export function listAdminWebsites(token: string, search = ""): Promise<AdminWebsite[]> {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  const qs = params.toString();
  return apiRequest<AdminWebsite[]>(`/admin/websites${qs ? `?${qs}` : ""}`, { method: "GET" }, token);
}

export function adminStopWebsite(token: string, id: string): Promise<AdminWebsite> {
  return apiRequest<AdminWebsite>(`/admin/websites/${id}/stop`, { method: "POST" }, token);
}

export function adminRestartWebsite(token: string, id: string): Promise<AdminWebsite> {
  return apiRequest<AdminWebsite>(`/admin/websites/${id}/restart`, { method: "POST" }, token);
}

export function adminDeleteWebsite(token: string, id: string): Promise<void> {
  return apiRequest<void>(`/admin/websites/${id}`, { method: "DELETE" }, token);
}

export function adminGetWebsiteLogs(token: string, id: string): Promise<{ logs: string }> {
  return apiRequest<{ logs: string }>(`/admin/websites/${id}/logs`, { method: "GET" }, token);
}

// ---------------------------------------------------------------------------
// System / metrics / containers
// ---------------------------------------------------------------------------

export interface SystemSnapshot {
  cpu_percent: number;
  memory_percent: number;
  memory_total_bytes: number;
  memory_used_bytes: number;
  disk_percent: number;
  disk_total_bytes: number;
  disk_used_bytes: number;
  network_rx_bytes: number;
  network_tx_bytes: number;
  uptime_seconds: number;
  services: ServiceStatus[];
}

export function getSystemSnapshot(token: string): Promise<SystemSnapshot> {
  return apiRequest<SystemSnapshot>("/admin/system", { method: "GET" }, token);
}

export type MetricsRange = "1h" | "24h" | "7d" | "30d";

export interface MetricPoint {
  timestamp: string;
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  network_rx_bytes: number;
  network_tx_bytes: number;
}

export interface MetricsHistory {
  range: MetricsRange;
  points: MetricPoint[];
}

export function getMetricsHistory(token: string, range: MetricsRange): Promise<MetricsHistory> {
  return apiRequest<MetricsHistory>(`/admin/metrics?range=${range}`, { method: "GET" }, token);
}

export interface ContainerSummary {
  id: string;
  name: string;
  status: string;
  image: string;
  cpu_percent: number | null;
  memory_bytes: number | null;
  memory_limit_bytes: number | null;
  website_id: string | null;
  website_name: string | null;
}

export function listContainers(token: string): Promise<ContainerSummary[]> {
  return apiRequest<ContainerSummary[]>("/admin/containers", { method: "GET" }, token);
}

export function getContainerLogs(token: string, containerId: string): Promise<{ logs: string }> {
  return apiRequest<{ logs: string }>(`/admin/containers/${containerId}/logs`, { method: "GET" }, token);
}

// ---------------------------------------------------------------------------
// Audit logs
// ---------------------------------------------------------------------------

export interface AuditLogEntry {
  id: number;
  actor_id: number | null;
  actor_name: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  description: string | null;
  ip_address: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

export function listAuditLogs(
  token: string,
  filters: { action?: string; range?: "24h" | "7d" | "30d"; page?: number; pageSize?: number }
): Promise<AuditLogListResponse> {
  const params = new URLSearchParams();
  if (filters.action) params.set("action", filters.action);
  if (filters.range) params.set("range", filters.range);
  params.set("page", String(filters.page ?? 1));
  params.set("page_size", String(filters.pageSize ?? 50));
  return apiRequest<AuditLogListResponse>(`/admin/audit-logs?${params}`, { method: "GET" }, token);
}

export function getAuditLog(token: string, id: number): Promise<AuditLogEntry> {
  return apiRequest<AuditLogEntry>(`/admin/audit-logs/${id}`, { method: "GET" }, token);
}
