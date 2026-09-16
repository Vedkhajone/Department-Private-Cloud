import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Cpu, Database, HardDrive, MemoryStick } from "lucide-react";

import { getContainerLogs, getSystemSnapshot, listContainers, type ContainerSummary, type SystemSnapshot } from "../../api/admin";
import { ApiError } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { ServiceStatusList } from "../../components/admin/ServiceStatusList";
import { useAuth } from "../../context/AuthContext";
import { formatBytes, formatUptime } from "../../utils/format";

function ResourceBar({ label, percent, icon }: { label: string; percent: number; icon: ReactNode }) {
  return (
    <div className="resource-bar">
      <div className="resource-bar-label">
        {icon}
        <span>{label}</span>
        <span className="resource-bar-percent">{percent.toFixed(0)}%</span>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${Math.min(100, percent)}%` }} />
      </div>
    </div>
  );
}

export function AdminSystem() {
  const { token } = useAuth();
  const [snapshot, setSnapshot] = useState<SystemSnapshot | null>(null);
  const [containers, setContainers] = useState<ContainerSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [openLogsFor, setOpenLogsFor] = useState<string | null>(null);
  const [logsText, setLogsText] = useState("");
  const [logsLoading, setLogsLoading] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      const [snap, containerList] = await Promise.all([getSystemSnapshot(token), listContainers(token)]);
      setSnapshot(snap);
      setContainers(containerList);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load server metrics. The monitoring service may be temporarily unavailable.");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [load]);

  async function handleShowLogs(container: ContainerSummary) {
    if (!token) return;
    setOpenLogsFor(container.id);
    setLogsLoading(true);
    setLogsText("");
    try {
      const result = await getContainerLogs(token, container.id);
      setLogsText(result.logs);
    } catch (err) {
      setLogsText(err instanceof ApiError ? err.message : "Failed to load logs");
    } finally {
      setLogsLoading(false);
    }
  }

  if (error) {
    return (
      <div className="card">
        <p className="form-error">{error}</p>
        <button type="button" className="btn btn-secondary" onClick={load}>
          Retry
        </button>
      </div>
    );
  }

  if (isLoading || !snapshot) return <p className="section-loading">Loading system status...</p>;

  return (
    <>
      <div className="card">
        <h3 className="card-title" style={{ marginTop: 0 }}>
          Server Health
        </h3>
        <ResourceBar label="CPU" percent={snapshot.cpu_percent} icon={<Cpu size={15} />} />
        <ResourceBar label="Memory" percent={snapshot.memory_percent} icon={<MemoryStick size={15} />} />
        <ResourceBar label="Disk" percent={snapshot.disk_percent} icon={<HardDrive size={15} />} />
        <div className="system-footer-stats">
          <span>
            Memory: {formatBytes(snapshot.memory_used_bytes)} / {formatBytes(snapshot.memory_total_bytes)}
          </span>
          <span>
            Disk: {formatBytes(snapshot.disk_used_bytes)} / {formatBytes(snapshot.disk_total_bytes)}
          </span>
          <span>Uptime: {formatUptime(snapshot.uptime_seconds)}</span>
        </div>
      </div>

      <div className="admin-two-col">
        <div className="card">
          <h3 className="card-title" style={{ marginTop: 0 }}>
            System Status
          </h3>
          <ServiceStatusList services={snapshot.services} />
        </div>

        <div className="card">
          <h3 className="card-title" style={{ marginTop: 0 }}>
            <Database size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
            Network
          </h3>
          <div className="detail-list">
            <div className="detail-row">
              <dt>Received</dt>
              <dd>{formatBytes(snapshot.network_rx_bytes)}</dd>
            </div>
            <div className="detail-row">
              <dt>Transmitted</dt>
              <dd>{formatBytes(snapshot.network_tx_bytes)}</dd>
            </div>
          </div>
        </div>
      </div>

      <div className="card section-card">
        <h3 className="card-title" style={{ marginTop: 0 }}>
          Containers
        </h3>
        {containers.length === 0 ? (
          <EmptyState icon={<HardDrive size={24} />} title="No managed containers" description="Dynamic website containers will appear here once deployed." />
        ) : (
          <div className="table-scroll">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Website</th>
                  <th>Status</th>
                  <th>CPU</th>
                  <th>Memory</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {containers.map((c) => (
                  <tr key={c.id}>
                    <td>{c.name}</td>
                    <td>{c.website_name ?? "—"}</td>
                    <td>
                      <span className={c.status === "running" ? "status-ok" : "status-neutral"}>{c.status}</span>
                    </td>
                    <td>{c.cpu_percent !== null ? `${c.cpu_percent.toFixed(1)}%` : "—"}</td>
                    <td>{c.memory_bytes !== null ? formatBytes(c.memory_bytes) : "—"}</td>
                    <td>
                      <button type="button" className="table-action-btn" onClick={() => handleShowLogs(c)}>
                        Logs
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {openLogsFor && (
          <div className="logs-panel">
            <div className="logs-panel-header">
              <strong>Container Logs</strong>
              <button type="button" onClick={() => setOpenLogsFor(null)}>
                Close
              </button>
            </div>
            <pre className="logs-panel-body">{logsLoading ? "Loading..." : logsText || "(no logs)"}</pre>
          </div>
        )}
      </div>
    </>
  );
}
