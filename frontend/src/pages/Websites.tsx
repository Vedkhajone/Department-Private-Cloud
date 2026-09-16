import { useCallback, useEffect, useMemo, useState } from "react";
import { Globe, Plus } from "lucide-react";

import { ApiError } from "../api/client";
import {
  deleteWebsite,
  getWebsiteLogs,
  listWebsites,
  restartWebsite,
  startWebsite,
  stopWebsite,
  type Website,
} from "../api/websites";
import { DeployWebsiteModal } from "../components/DeployWebsiteModal";
import { EmptyState } from "../components/EmptyState";
import { WebsiteCard } from "../components/WebsiteCard";
import { useAuth } from "../context/AuthContext";

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
  const [showDeployModal, setShowDeployModal] = useState(false);

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
    <div className="card section-card">
      <div className="section-header">
        <div className="section-header-title">
          <span className="section-icon accent-green">
            <Globe size={18} />
          </span>
          <div>
            <h3>My Websites</h3>
            <p>Host and manage your websites</p>
          </div>
        </div>

        <button type="button" className="btn btn-primary" onClick={() => setShowDeployModal(true)}>
          <Plus size={15} /> Deploy Website
        </button>
      </div>

      {error && <p className="form-error">{error}</p>}

      {isLoading ? (
        <p className="section-loading">Loading...</p>
      ) : websites.length === 0 ? (
        <EmptyState
          icon={<Globe size={28} />}
          title="No websites deployed yet"
          description="Deploy a ZIP to publish your first static or dynamic website."
        />
      ) : (
        <div className="website-grid">
          {websites.map((site) => (
            <WebsiteCard
              key={site.id}
              site={site}
              onDelete={handleDelete}
              onStart={handleStart}
              onStop={handleStop}
              onRestart={handleRestart}
              onShowLogs={handleShowLogs}
              logsOpen={openLogsFor === site.id}
              logsText={logsText}
              logsLoading={logsLoading}
              onCloseLogs={() => setOpenLogsFor(null)}
            />
          ))}
        </div>
      )}

      {showDeployModal && (
        <DeployWebsiteModal onClose={() => setShowDeployModal(false)} onDeployed={refresh} />
      )}
    </div>
  );
}
