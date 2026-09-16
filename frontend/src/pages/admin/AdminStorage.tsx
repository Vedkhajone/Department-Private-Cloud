import { useCallback, useEffect, useState } from "react";
import { HardDrive } from "lucide-react";

import { getStorageOverview, type StorageOverview } from "../../api/admin";
import { ApiError } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { formatBytes } from "../../utils/format";

const HEALTH_LABEL: Record<StorageOverview["health"], string> = {
  normal: "Normal",
  warning: "Warning",
  critical: "Critical",
};

const HEALTH_CLASS: Record<StorageOverview["health"], string> = {
  normal: "status-ok",
  warning: "status-amber",
  critical: "status-bad",
};

export function AdminStorage({ onOpenUser }: { onOpenUser: (userId: number) => void }) {
  const { token } = useAuth();
  const [data, setData] = useState<StorageOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setData(await getStorageOverview(token));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load storage data");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  if (isLoading || !data) return <p className="section-loading">Loading storage data...</p>;
  if (error) return <p className="form-error">{error}</p>;

  const topMax = Math.max(...data.top_users.map((u) => u.storage_used_bytes), 1);

  return (
    <>
      <div className="admin-stat-grid">
        <div className="card stat-card">
          <div className="stat-card-top">
            <span className="stat-card-icon accent-blue">
              <HardDrive size={18} />
            </span>
            <span className="stat-card-label">Total Storage</span>
          </div>
          <div className="stat-card-value">{formatBytes(data.capacity_bytes)}</div>
        </div>
        <div className="card stat-card">
          <div className="stat-card-top">
            <span className="stat-card-label">Used</span>
          </div>
          <div className="stat-card-value">{formatBytes(data.used_bytes)}</div>
          <div className="stat-card-sublabel">{data.used_percent.toFixed(1)}%</div>
        </div>
        <div className="card stat-card">
          <div className="stat-card-top">
            <span className="stat-card-label">Available</span>
          </div>
          <div className="stat-card-value">{formatBytes(data.available_bytes)}</div>
        </div>
        <div className="card stat-card">
          <div className="stat-card-top">
            <span className="stat-card-label">Files / Folders / Users</span>
          </div>
          <div className="stat-card-value">
            {data.file_count} / {data.folder_count} / {data.user_count}
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title" style={{ marginTop: 0 }}>
          Storage Health
        </h3>
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${Math.min(100, data.used_percent)}%` }} />
        </div>
        <div className="storage-health-legend">
          <span className={HEALTH_CLASS[data.health]}>● {HEALTH_LABEL[data.health]}</span>
          <span className="section-loading" style={{ padding: 0 }}>
            Warning ≥ {data.warning_threshold_percent}% · Critical ≥ {data.critical_threshold_percent}%
          </span>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title" style={{ marginTop: 0 }}>
          Storage Usage by User
        </h3>
        {data.top_users.length === 0 ? (
          <p className="section-loading">No files uploaded yet.</p>
        ) : (
          <ul className="bar-list">
            {data.top_users.map((u) => (
              <li key={u.user_id} className="bar-row" onClick={() => onOpenUser(u.user_id)}>
                <span className="bar-label">{u.name}</span>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${(u.storage_used_bytes / topMax) * 100}%` }} />
                </div>
                <span className="bar-value">{formatBytes(u.storage_used_bytes)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
