import {
  Cloud,
  FileClock,
  Globe,
  HardDrive,
  LayoutDashboard,
  LogOut,
  Server,
  Settings as SettingsIcon,
  Users,
} from "lucide-react";

import type { User } from "../../api/auth";
import type { AdminView } from "../../types";

interface AdminSidebarProps {
  activeView: AdminView;
  onNavigate: (view: AdminView) => void;
  onLogout: () => void;
  user: User;
}

const NAV_ITEMS: { view: AdminView; label: string; icon: typeof LayoutDashboard }[] = [
  { view: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { view: "users", label: "Users", icon: Users },
  { view: "storage", label: "Storage", icon: HardDrive },
  { view: "websites", label: "Websites", icon: Globe },
  { view: "system", label: "System", icon: Server },
  { view: "activity", label: "Activity Logs", icon: FileClock },
  { view: "settings", label: "Settings", icon: SettingsIcon },
];

function initial(name: string): string {
  return (name.trim()[0] || "?").toUpperCase();
}

export function AdminSidebar({ activeView, onNavigate, onLogout, user }: AdminSidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="brand-icon">
          <Cloud size={20} />
        </span>
        <div>
          <div className="brand-name">ECE DeptCloud</div>
          <div className="brand-subtitle">The ECE Department Private Cloud</div>
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
            <div className="sidebar-user-role">Administrator</div>
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
