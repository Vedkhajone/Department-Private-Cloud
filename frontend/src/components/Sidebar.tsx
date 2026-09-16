import { Cloud, Folder, Globe, LayoutDashboard, LogOut, Settings as SettingsIcon } from "lucide-react";

import type { User } from "../api/auth";
import type { DashboardView } from "../types";

interface SidebarProps {
  activeView: DashboardView;
  onNavigate: (view: DashboardView) => void;
  onLogout: () => void;
  user: User;
}

const NAV_ITEMS: { view: DashboardView; label: string; icon: typeof LayoutDashboard }[] = [
  { view: "overview", label: "Dashboard", icon: LayoutDashboard },
  { view: "files", label: "My Files", icon: Folder },
  { view: "websites", label: "My Websites", icon: Globe },
  { view: "settings", label: "Settings", icon: SettingsIcon },
];

function initial(name: string): string {
  return (name.trim()[0] || "?").toUpperCase();
}

export function Sidebar({ activeView, onNavigate, onLogout, user }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="brand-icon">
          <Cloud size={20} />
        </span>
        <div>
          <div className="brand-name">DECP</div>
          <div className="brand-subtitle">Department Engineering Cloud</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ view, label, icon: Icon }) => (
          <button
            key={view}
            type="button"
            className={`sidebar-nav-item${activeView === view ? " active" : ""}`}
            onClick={() => onNavigate(view)}
          >
            <Icon size={18} />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <span className="avatar avatar-neutral">{initial(user.name)}</span>
          <div>
            <div className="sidebar-user-name">{user.name}</div>
            <div className="sidebar-user-role">{user.role}</div>
          </div>
        </div>
        <button type="button" className="sidebar-logout" onClick={onLogout}>
          <LogOut size={16} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
