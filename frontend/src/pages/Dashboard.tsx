import { useState } from "react";
import { Folder, Globe } from "lucide-react";

import { useAuth } from "../context/AuthContext";
import { AccountCard } from "../components/AccountCard";
import { Footer } from "../components/Footer";
import { QuickActionCard } from "../components/QuickActionCard";
import { Sidebar } from "../components/Sidebar";
import { StorageCard } from "../components/StorageCard";
import { TopHeader } from "../components/TopHeader";
import type { DashboardView } from "../types";
import { Files } from "./Files";
import { Settings } from "./Settings";
import { Websites } from "./Websites";

function greetingName(name: string): string {
  return name.trim().split(/\s+/)[0] || name;
}

function todayLabel(): string {
  return new Date().toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function Dashboard() {
  const { user, logout } = useAuth();
  const [view, setView] = useState<DashboardView>("overview");

  if (!user) return null;

  return (
    <div className="app-shell">
      <Sidebar activeView={view} onNavigate={setView} onLogout={logout} user={user} />

      <div className="app-main">
        <TopHeader user={user} />

        <main className="app-content">
          {view === "overview" && (
            <>
              <section className="welcome-section">
                <div>
                  <h1 className="welcome-title">Welcome back, {greetingName(user.name)} 👋</h1>
                  <p className="welcome-subtitle">
                    Manage your files, websites and more from your personal cloud.
                  </p>
                </div>
                <div className="welcome-meta">
                  <div className="welcome-date">{todayLabel()}</div>
                  <div className="welcome-quote">&ldquo;Build today, a better tomorrow.&rdquo;</div>
                </div>
              </section>

              <div className="overview-grid">
                <AccountCard user={user} />

                <div className="overview-right">
                  <StorageCard />

                  <div className="quick-actions-row">
                    <QuickActionCard
                      icon={<Folder size={20} />}
                      title="My Files"
                      description="Store, manage and access your files"
                      accent="blue"
                      onClick={() => setView("files")}
                    />
                    <QuickActionCard
                      icon={<Globe size={20} />}
                      title="My Websites"
                      description="Deploy and manage your websites"
                      accent="green"
                      onClick={() => setView("websites")}
                    />
                  </div>
                </div>
              </div>

              <Files />
              <Websites />
            </>
          )}

          {view === "files" && (
            <>
              <button type="button" className="back-link" onClick={() => setView("overview")}>
                ← Back to Dashboard
              </button>
              <Files />
            </>
          )}

          {view === "websites" && (
            <>
              <button type="button" className="back-link" onClick={() => setView("overview")}>
                ← Back to Dashboard
              </button>
              <Websites />
            </>
          )}

          {view === "settings" && <Settings />}
        </main>

        <Footer />
      </div>
    </div>
  );
}
