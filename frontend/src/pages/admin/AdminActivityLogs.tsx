import { useCallback, useEffect, useState } from "react";
import { FileClock } from "lucide-react";

import { listAuditLogs, type AuditLogEntry } from "../../api/admin";
import { ApiError } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { useAuth } from "../../context/AuthContext";
import { formatDateTime } from "../../utils/format";

type RangeFilter = "" | "24h" | "7d" | "30d";

const ACTIONS = [
  "",
  "auth.register",
  "auth.login_success",
  "auth.login_failure",
  "file.upload",
  "file.delete",
  "folder.create",
  "folder.delete",
  "website.deploy",
  "website.delete",
  "website.restart",
  "website.stop",
  "admin.role_change",
  "admin.account_status_change",
];

export function AdminActivityLogs() {
  const { token } = useAuth();
  const [action, setAction] = useState("");
  const [range, setRange] = useState<RangeFilter>("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<AuditLogEntry | null>(null);

  const pageSize = 25;

  const load = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await listAuditLogs(token, {
        action: action || undefined,
        range: range || undefined,
        page,
        pageSize,
      });
      setItems(result.items);
      setTotal(result.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load activity logs");
    } finally {
      setIsLoading(false);
    }
  }, [token, action, range, page]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="card section-card">
      <div className="section-header">
        <div className="section-header-title">
          <span className="section-icon accent-blue">
            <FileClock size={18} />
          </span>
          <div>
            <h3>Activity Logs</h3>
            <p>{total} recorded events</p>
          </div>
        </div>
      </div>

      <div className="filter-row">
        <select
          value={action}
          onChange={(e) => {
            setAction(e.target.value);
            setPage(1);
          }}
        >
          {ACTIONS.map((a) => (
            <option key={a} value={a}>
              {a || "All Actions"}
            </option>
          ))}
        </select>
        <select
          value={range}
          onChange={(e) => {
            setRange(e.target.value as RangeFilter);
            setPage(1);
          }}
        >
          <option value="">All Time</option>
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
        </select>
      </div>

      {error && <p className="form-error">{error}</p>}

      {isLoading ? (
        <p className="section-loading">Loading...</p>
      ) : items.length === 0 ? (
        <EmptyState icon={<FileClock size={28} />} title="No activity found" description="Try adjusting your filters." />
      ) : (
        <>
          <ul className="activity-list">
            {items.map((entry) => (
              <li key={entry.id} className="activity-row activity-row-clickable" onClick={() => setSelected(entry)}>
                <div>
                  <span className="activity-actor">{entry.actor_name ?? "System"}</span>{" "}
                  <span className="activity-desc">{entry.description ?? entry.action}</span>
                </div>
                <span className="activity-time">{formatDateTime(entry.created_at)}</span>
              </li>
            ))}
          </ul>

          {totalPages > 1 && (
            <div className="pagination">
              <button type="button" className="btn btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Previous
              </button>
              <span>
                Page {page} of {totalPages}
              </span>
              <button type="button" className="btn btn-secondary" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                Next
              </button>
            </div>
          )}
        </>
      )}

      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Activity Details</h3>
              <button type="button" className="icon-button" onClick={() => setSelected(null)}>
                ×
              </button>
            </div>
            <dl className="detail-list">
              <div className="detail-row">
                <dt>Action</dt>
                <dd>{selected.action}</dd>
              </div>
              <div className="detail-row">
                <dt>User</dt>
                <dd>{selected.actor_name ?? "System"}</dd>
              </div>
              {selected.resource_type && (
                <div className="detail-row">
                  <dt>Resource</dt>
                  <dd>{selected.resource_type}</dd>
                </div>
              )}
              <div className="detail-row">
                <dt>Time</dt>
                <dd>{formatDateTime(selected.created_at)}</dd>
              </div>
              {selected.ip_address && (
                <div className="detail-row">
                  <dt>IP Address</dt>
                  <dd>{selected.ip_address}</dd>
                </div>
              )}
            </dl>
            {selected.description && (
              <>
                <h4 className="card-title" style={{ marginBottom: "0.3rem" }}>
                  Details
                </h4>
                <p className="section-loading" style={{ padding: 0 }}>
                  {selected.description}
                </p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
