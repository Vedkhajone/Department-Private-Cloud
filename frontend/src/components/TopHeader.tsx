import { Bell, ChevronDown } from "lucide-react";

import type { User } from "../api/auth";
import { ThemeToggle } from "./ThemeToggle";

function initial(name: string): string {
  return (name.trim()[0] || "?").toUpperCase();
}

export function TopHeader({ user }: { user: User }) {
  return (
    <header className="top-header">
      <ThemeToggle />

      {/* Visual only -- DECP has no notification system yet, so this
          intentionally does nothing when clicked rather than faking one. */}
      <button type="button" className="icon-button" aria-label="Notifications">
        <Bell size={18} />
      </button>

      <div className="top-header-user">
        <span className="avatar avatar-neutral avatar-sm">{initial(user.name)}</span>
        <span className="top-header-name">{user.name}</span>
        <ChevronDown size={14} className="top-header-chevron" />
      </div>
    </header>
  );
}
