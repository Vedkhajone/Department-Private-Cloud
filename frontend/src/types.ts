// Shared, dependency-free types used across components -- kept in
// their own module (rather than re-exported from a page like
// Dashboard.tsx) specifically to avoid circular imports between
// pages/Dashboard.tsx and components/Sidebar.tsx.
export type DashboardView = "overview" | "files" | "websites" | "settings";

export type AdminView =
  | "dashboard"
  | "users"
  | "storage"
  | "websites"
  | "system"
  | "activity"
  | "settings";
