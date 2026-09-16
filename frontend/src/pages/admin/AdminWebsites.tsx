import { Fragment, useCallback, useEffect, useState } from "react";
import { ExternalLink, Globe, Search } from "lucide-react";

import {
  adminDeleteWebsite,
  adminGetWebsiteLogs,
  adminRestartWebsite,
  adminStopWebsite,
  listAdminWebsites,
  type AdminWebsite,
} from "../../api/admin";
import { ApiError } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { StatusDot } from "../../components/StatusDot";
import { useAuth } from "../../context/AuthContext";
import { formatDate } from "../../utils/format";

const FRAMEWORK_LABEL: Record<AdminWebsite["framework"], string> = {
  html: "Static HTML",
  react: "React / Vite",
  flask: "Dynamic — Flask",
  fastapi: "Dynamic — FastAPI",
  node: "Dynamic — Node.js",
};

export function AdminWebsites() {
  const { token } = useAuth();
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<AdminWebsite[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openLogsFor, setOpenLogsFor] = useState<string | null>(null);
  const [logsText, setLogsText] = useState("");
  const [logsLoading, setLogsLoading] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      setItems(await listAdminWebsites(token, search));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load websites");
    } finally {
      setIsLoading(false);
    }
  }, [token, search]);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  async function withErrorHandling(action: () => Promise<unknown>, fallback: string) {
    if (!token) return;
    try {
      await action();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fallback);
    }
  }

  function handleStop(site: AdminWebsite) {
    void withErrorHandling(() => adminStopWebsite(token!, site.id), "Stop failed");
  }

  function handleRestart(site: AdminWebsite) {
    void withErrorHandling(() => adminRestartWebsite(token!, site.id), "Restart failed");
  }

  function handleDelete(site: AdminWebsite) {
    if (!window.confirm(`Delete "${site.name}"?\n\nThis will permanently remove the website deployment.`)) return;
    void withErrorHandling(() => adminDeleteWebsite(token!, site.id), "Delete failed");
  }

  async function handleShowLogs(site: AdminWebsite) {
    if (!token) return;
    setOpenLogsFor(site.id);
    setLogsLoading(true);
    setLogsText("");
    try {
      const result = await adminGetWebsiteLogs(token, site.id);
      setLogsText(result.logs);
    } catch (err) {
      setLogsText(err instanceof ApiError ? err.message : "Failed to load logs");
    } finally {
      setLogsLoading(false);
    }
  }

  return (
    <div className="card section-card">
      <div className="section-header">
        <div className="section-header-title">
          <span className="section-icon accent-green">
            <Globe size={18} />
          </span>
          <div>
            <h3>Websites</h3>
            <p>All hosted websites across every user</p>
          </div>
        </div>
      </div>

      <div className="search-bar">
        <Search size={15} />
        <input
          type="text"
          placeholder="Search by website name or owner email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {error && <p className="form-error">{error}</p>}

      {isLoading ? (
        <p className="section-loading">Loading...</p>
      ) : items.length === 0 ? (
        <EmptyState icon={<Globe size={28} />} title="No websites found" description="No websites match your search." />
      ) : (
        <div className="table-scroll">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Website</th>
                <th>Owner</th>
                <th>Type</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((site) => (
                <Fragment key={site.id}>
                  <tr>
                    <td>{site.name}</td>
                    <td>{site.owner_name}</td>
                    <td>{FRAMEWORK_LABEL[site.framework]}</td>
                    <td>
                      <StatusDot status={site.status} />
                    </td>
                    <td>{formatDate(site.created_at)}</td>
                    <td>
                      <div className="table-actions">
                        {site.status === "online" && site.public_url && (
                          <a href={site.public_url} target="_blank" rel="noreferrer" className="icon-button" title="Open Website">
                            <ExternalLink size={15} />
                          </a>
                        )}
                        {site.type === "dynamic" && (
                          <>
                            {site.status === "online" && (
                              <button type="button" className="table-action-btn" onClick={() => handleStop(site)}>
                                Stop
                              </button>
                            )}
                            <button type="button" className="table-action-btn" onClick={() => handleRestart(site)}>
                              Restart
                            </button>
                            <button type="button" className="table-action-btn" onClick={() => handleShowLogs(site)}>
                              Logs
                            </button>
                          </>
                        )}
                        <button type="button" className="table-action-btn table-action-danger" onClick={() => handleDelete(site)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                  {openLogsFor === site.id && (
                    <tr>
                      <td colSpan={6}>
                        <div className="logs-panel">
                          <div className="logs-panel-header">
                            <strong>Logs — {site.name}</strong>
                            <button type="button" onClick={() => setOpenLogsFor(null)}>
                              Close
                            </button>
                          </div>
                          <pre className="logs-panel-body">{logsLoading ? "Loading..." : logsText || "(no logs)"}</pre>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
