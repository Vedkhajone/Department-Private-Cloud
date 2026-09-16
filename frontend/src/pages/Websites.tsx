import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import {
  deleteWebsite,
  deployWebsite,
  getWebsiteLogs,
  listWebsites,
  restartWebsite,
  startWebsite,
  stopWebsite,
  type Website,
} from "../api/websites";
import { useAuth } from "../context/AuthContext";

const FRAMEWORK_LABEL: Record<Website["framework"], string> = {
  html: "Static HTML",
  react: "React / Vite",
  flask: "Dynamic — Flask",
  fastapi: "Dynamic — FastAPI",
  node: "Dynamic — Node.js",
};

const STATUS_CLASS: Record<Website["status"], string> = {
  pending: "status-neutral",
  building: "status-neutral",
  online: "status-ok",
  stopped: "status-neutral",
  failed: "status-bad",
  deleting: "status-neutral",
};

/**
 * "My Websites": deploy a ZIP as a static or dynamic website, see its
 * status, and manage it (open/start/stop/restart/logs/delete). Sites
 * still building/pending are polled every few seconds until they
 * settle into "online" or "failed".
 */
export function Websites() {
  const { token } = useAuth();
  const [websites, setWebsites] = useState<Website[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showDeployForm, setShowDeployForm] = useState(false);
  const [deployName, setDeployName] = useState("");
  const [deployFile, setDeployFile] = useState<File | null>(null);
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployError, setDeployError] = useState<string | null>(null);

  const [openLogsFor, setOpenLogsFor] = useState<string | null>(null);
  const [logsText, setLogsText] = useState<string>("");
  const [logsLoading, setLogsLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      const list = await listWebsites(token);
      setWebsites(list);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load websites");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const hasInFlightDeployment = useMemo(
    () => websites.some((w) => w.status === "pending" || w.status === "building"),
    [websites]
  );

  useEffect(() => {
    if (!hasInFlightDeployment) return;
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, [hasInFlightDeployment, refresh]);

  async function handleDeploy(e: FormEvent) {
    e.preventDefault();
    if (!token || !deployFile) return;
    setIsDeploying(true);
    setDeployError(null);
    try {
      await deployWebsite(token, deployName, deployFile);
      setShowDeployForm(false);
      setDeployName("");
      setDeployFile(null);
      await refresh();
    } catch (err) {
      setDeployError(err instanceof ApiError ? err.message : "Deployment failed");
    } finally {
      setIsDeploying(false);
    }
  }

  async function withErrorHandling(action: () => Promise<unknown>, fallback: string) {
    if (!token) return;
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fallback);
    }
  }

  function handleDelete(site: Website) {
    if (!window.confirm(`Delete "${site.name}"? This cannot be undone.`)) return;
    void withErrorHandling(() => deleteWebsite(token!, site.id), "Delete failed");
  }

  function handleStop(site: Website) {
    void withErrorHandling(() => stopWebsite(token!, site.id), "Stop failed");
  }

  function handleStart(site: Website) {
    void withErrorHandling(() => startWebsite(token!, site.id), "Start failed");
  }

  function handleRestart(site: Website) {
    void withErrorHandling(() => restartWebsite(token!, site.id), "Restart failed");
  }

  async function handleShowLogs(site: Website) {
    if (!token) return;
    setOpenLogsFor(site.id);
    setLogsLoading(true);
    setLogsText("");
    try {
      const result = await getWebsiteLogs(token, site.id);
      setLogsText(result.logs);
    } catch (err) {
      setLogsText(err instanceof ApiError ? err.message : "Failed to load logs");
    } finally {
      setLogsLoading(false);
    }
  }

  return (
    <div className="files-card">
      <div className="files-header">
        <h2>My Websites</h2>
      </div>

      <div className="files-toolbar">
        <button type="button" onClick={() => setShowDeployForm((v) => !v)}>
          {showDeployForm ? "Cancel" : "+ Deploy Website"}
        </button>
      </div>

      {showDeployForm && (
        <form className="deploy-form" onSubmit={handleDeploy}>
          <label>
            Website Name
            <input
              type="text"
              value={deployName}
              onChange={(e) => setDeployName(e.target.value)}
              required
            />
          </label>

          <label>
            Upload ZIP
            <input
              type="file"
              accept=".zip"
              onChange={(e) => setDeployFile(e.target.files?.[0] ?? null)}
              required
            />
          </label>

          {deployError && <p className="form-error">{deployError}</p>}

          <button type="submit" disabled={isDeploying || !deployFile}>
            {isDeploying ? "Uploading..." : "Analyze / Deploy"}
          </button>
        </form>
      )}

      {error && <p className="form-error">{error}</p>}

      {isLoading ? (
        <p>Loading...</p>
      ) : websites.length === 0 ? (
        <p className="empty-row">No websites deployed yet.</p>
      ) : (
        <ul className="website-list">
          {websites.map((site) => (
            <li key={site.id} className="website-row">
              <div className="website-info">
                <div className="website-name">{site.name}</div>
                <div className="website-meta">
                  Type: {FRAMEWORK_LABEL[site.framework]}
                  {"  ·  "}
                  Status: <span className={STATUS_CLASS[site.status]}>{site.status}</span>
                  {"  ·  "}
                  {new Date(site.created_at).toLocaleDateString()}
                </div>
                {site.status === "failed" && site.error_message && (
                  <div className="form-error website-error">{site.error_message}</div>
                )}
              </div>

              <div className="file-actions website-actions">
                {site.status === "online" && site.public_url && (
                  <a href={site.public_url} target="_blank" rel="noreferrer">
                    <button type="button">Open Website</button>
                  </a>
                )}

                {site.type === "dynamic" && (
                  <>
                    {site.status === "online" && (
                      <button type="button" onClick={() => handleStop(site)}>
                        Stop
                      </button>
                    )}
                    {site.status === "stopped" && (
                      <button type="button" onClick={() => handleStart(site)}>
                        Start
                      </button>
                    )}
                    {(site.status === "online" || site.status === "stopped") && (
                      <button type="button" onClick={() => handleRestart(site)}>
                        Restart
                      </button>
                    )}
                    <button type="button" onClick={() => handleShowLogs(site)}>
                      Logs
                    </button>
                  </>
                )}

                <button type="button" onClick={() => handleDelete(site)}>
                  Delete
                </button>
              </div>

              {openLogsFor === site.id && (
                <div className="logs-panel">
                  <div className="logs-panel-header">
                    <strong>Logs</strong>
                    <button type="button" onClick={() => setOpenLogsFor(null)}>
                      Close
                    </button>
                  </div>
                  <pre className="logs-panel-body">
                    {logsLoading ? "Loading..." : logsText || "(no logs)"}
                  </pre>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
