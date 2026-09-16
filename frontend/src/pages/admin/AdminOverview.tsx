import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Cloud, Globe, Users } from "lucide-react";

import {
  getMetricsHistory,
  getOverview,
  listAuditLogs,
  type AdminOverview as AdminOverviewData,
  type AuditLogEntry,
  type MetricsRange,
} from "../../api/admin";
import { ApiError } from "../../api/client";
import { LineChart } from "../../components/admin/LineChart";
import { ServiceStatusList } from "../../components/admin/ServiceStatusList";
import { StatCard } from "../../components/admin/StatCard";
import { EmptyState } from "../../components/EmptyState";
import { useAuth } from "../../context/AuthContext";
import { formatBytes, formatDateTime } from "../../utils/format";

const RANGE_LABEL: Record<MetricsRange, string> = {
  "1h": "Last 1 hour",
  "24h": "Last 24 hours",
  "7d": "Last 7 days",
  "30d": "Last 30 days",
};

function todayLabel(): string {
  return new Date().toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function AdminOverview() {
  const { token, user } = useAuth();
  const [overview, setOverview] = useState<AdminOverviewData | null>(null);
  const [activity, setActivity] = useState<AuditLogEntry[]>([]);
  const [range, setRange] = useState<MetricsRange>("1h");
  const [cpuPoints, setCpuPoints] = useState<{ x: number; y: number }[]>([]);
  const [memPoints, setMemPoints] = useState<{ x: number; y: number }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadOverview = useCallback(async () => {
    if (!token) return;
    try {
      const [ov, logs] = await Promise.all([
        getOverview(token),
        listAuditLogs(token, { page: 1, pageSize: 6 }),
      ]);
      setOverview(ov);
      setActivity(logs.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load the admin overview.");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  const loadMetrics = useCallback(async () => {
    if (!token) return;
    try {
      const history = await getMetricsHistory(token, range);
      setCpuPoints(
        history.points.map((p) => ({ x: new Date(p.timestamp).getTime(), y: p.cpu_percent }))
      );
      setMemPoints(
        history.points.map((p) => ({ x: new Date(p.timestamp).getTime(), y: p.memory_percent }))
      );
    } catch {
      // Non-fatal -- the charts just show "not enough data" below.
    }
  }, [token, range]);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    loadMetrics();
  }, [loadMetrics]);

  // Refresh the overview + metrics periodically without reloading the
  // whole page -- see docs/ADMIN-DASHBOARD.md, "Auto-refresh."
  useEffect(() => {
    const t = setInterval(() => {
      loadOverview();
      loadMetrics();
    }, 30000);
    return () => clearInterval(t);
  }, [loadOverview, loadMetrics]);

  if (error) {
    return (
      <div className="card">
        <p className="form-error">{error}</p>
        <button type="button" className="btn btn-secondary" onClick={loadOverview}>
          Retry
        </button>
      </div>
    );
  }

  if (isLoading || !overview || !user) {
    return <p className="section-loading">Loading admin dashboard...</p>;
  }

  return (
    <>
      <section className="welcome-section">
        <div>
          <h1 className="welcome-title">Welcome back, {user.name.split(" ")[0]} 👋</h1>
          <p className="welcome-subtitle">Monitor and manage your department cloud.</p>
        </div>
        <div className="welcome-meta">
          <div className="welcome-date">{todayLabel()}</div>
        </div>
      </section>

      <div className="admin-stat-grid">
        <StatCard
          icon={<Users size={18} />}
          label="Total Users"
          value={String(overview.total_users)}
          sublabel={`+${overview.new_users_this_month} this month`}
          accent="blue"
        />
        <StatCard
          icon={<Cloud size={18} />}
          label="Storage Used"
          value={formatBytes(overview.storage_used_bytes)}
          sublabel={`${overview.storage_percent.toFixed(1)}% of capacity`}
          accent="blue"
        />
        <StatCard
          icon={<Globe size={18} />}
          label="Websites"
          value={String(overview.websites_total)}
          sublabel={`${overview.websites_static} static · ${overview.websites_dynamic} dynamic`}
          accent="green"
        />
        <StatCard
          icon={<CheckCircle2 size={18} />}
          label="Online Services"
          value={`${overview.services_online} / ${overview.services_total}`}
          sublabel={overview.services_online === overview.services_total ? "All healthy" : "Attention needed"}
          accent={overview.services_online === overview.services_total ? "green" : "amber"}
        />
      </div>

      <div className="admin-two-col">
        <div className="card">
          <div className="chart-card-header">
            <h3 className="card-title" style={{ margin: 0 }}>
              CPU Usage
            </h3>
            <select
              className="range-select"
              value={range}
              onChange={(e) => setRange(e.target.value as MetricsRange)}
            >
              {(Object.keys(RANGE_LABEL) as MetricsRange[]).map((r) => (
                <option key={r} value={r}>
                  {RANGE_LABEL[r]}
                </option>
              ))}
            </select>
          </div>
          <LineChart points={cpuPoints} color="#2563eb" />
        </div>

        <div className="card">
          <h3 className="card-title" style={{ margin: 0 }}>
            Memory Usage
          </h3>
          <LineChart points={memPoints} color="#16a34a" />
        </div>
      </div>

      <div className="admin-two-col">
        <div className="card">
          <h3 className="card-title" style={{ marginTop: 0 }}>
            System Status
          </h3>
          <ServiceStatusList services={overview.services} />
        </div>

        <div className="card">
          <h3 className="card-title" style={{ marginTop: 0 }}>
            Recent Activity
          </h3>
          {activity.length === 0 ? (
            <EmptyState
              icon={<Globe size={24} />}
              title="No recent activity"
              description="Activity will appear here as users interact with the department cloud."
            />
          ) : (
            <ul className="activity-list">
              {activity.map((entry) => (
                <li key={entry.id} className="activity-row">
                  <div>
                    <span className="activity-actor">{entry.actor_name ?? "System"}</span>{" "}
                    <span className="activity-desc">{entry.description ?? entry.action}</span>
                  </div>
                  <span className="activity-time">{formatDateTime(entry.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  );
}
