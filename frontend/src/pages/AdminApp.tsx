import { useState } from "react";

import { AdminSidebar } from "../components/admin/AdminSidebar";
import { Footer } from "../components/Footer";
import { TopHeader } from "../components/TopHeader";
import { useAuth } from "../context/AuthContext";
import type { AdminView } from "../types";
import { AdminActivityLogs } from "./admin/AdminActivityLogs";
import { AdminOverview } from "./admin/AdminOverview";
import { AdminStorage } from "./admin/AdminStorage";
import { AdminSystem } from "./admin/AdminSystem";
import { AdminUserDetail } from "./admin/AdminUserDetail";
import { AdminUsers } from "./admin/AdminUsers";
import { AdminWebsites } from "./admin/AdminWebsites";
import { Settings } from "./Settings";

/**
 * The admin console shell: sidebar + top header + a view switcher,
 * mirroring pages/Dashboard.tsx's structure so the two feel like the
 * same product. Rendered instead of <Dashboard /> in App.tsx when the
 * authenticated user's role is "admin" -- see docs/ADMIN-DASHBOARD.md.
 */
export function AdminApp() {
  const { user, logout } = useAuth();
  const [view, setView] = useState<AdminView>("dashboard");
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);

  if (!user) return null;

  function openUser(userId: number) {
    setSelectedUserId(userId);
    setView("users");
  }

  function backToUserList() {
    setSelectedUserId(null);
  }

  return (
    <div className="app-shell">
      <AdminSidebar
        activeView={view}
        onNavigate={(v) => {
          setSelectedUserId(null);
          setView(v);
        }}
        onLogout={logout}
        user={user}
      />

      <div className="app-main">
        <TopHeader user={user} />

        <main className="app-content">
          {view === "dashboard" && <AdminOverview />}
          {view === "users" &&
            (selectedUserId !== null ? (
              <AdminUserDetail userId={selectedUserId} onBack={backToUserList} />
            ) : (
              <AdminUsers onOpenUser={openUser} />
            ))}
          {view === "storage" && <AdminStorage onOpenUser={openUser} />}
          {view === "websites" && <AdminWebsites />}
          {view === "system" && <AdminSystem />}
          {view === "activity" && <AdminActivityLogs />}
          {view === "settings" && <Settings />}
        </main>

        <Footer />
      </div>
    </div>
  );
}
