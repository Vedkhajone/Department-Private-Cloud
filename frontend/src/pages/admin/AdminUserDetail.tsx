import { useCallback, useEffect, useState } from "react";
import { Globe } from "lucide-react";

import { changeUserActive, changeUserRole, getUserDetail, type AdminUserDetail as UserDetailData } from "../../api/admin";
import type { UserRole } from "../../api/auth";
import { ApiError } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { useAuth } from "../../context/AuthContext";
import { formatBytes, formatDate } from "../../utils/format";

const ROLES: UserRole[] = ["student", "faculty", "admin"];

export function AdminUserDetail({ userId, onBack }: { userId: number; onBack: () => void }) {
  const { token, user: currentAdmin } = useAuth();
  const [detail, setDetail] = useState<UserDetailData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      setDetail(await getUserDetail(token, userId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load user");
    } finally {
      setIsLoading(false);
    }
  }, [token, userId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRoleChange(role: UserRole) {
    if (!token) return;
    setActionError(null);
    try {
      setDetail(await changeUserRole(token, userId, role));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to change role");
    }
  }

  async function handleActiveToggle() {
    if (!token || !detail) return;
    setActionError(null);
    try {
      setDetail(await changeUserActive(token, userId, !detail.is_active));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to update account status");
    }
  }

  const isSelf = currentAdmin?.id === userId;

  return (
    <div className="card section-card">
      <button type="button" className="back-link" onClick={onBack}>
        ← Back to Users
      </button>

      {error && <p className="form-error">{error}</p>}

      {isLoading || !detail ? (
        <p className="section-loading">Loading...</p>
      ) : (
        <>
          <div className="user-detail-header">
            <div>
              <h2 className="card-title" style={{ marginTop: 0 }}>
                {detail.name}
              </h2>
              <span className="badge">{detail.role}</span>{" "}
              <span className={detail.is_active ? "status-ok" : "status-bad"}>
                {detail.is_active ? "Active" : "Disabled"}
              </span>
            </div>
          </div>

          <dl className="detail-list">
            <div className="detail-row">
              <dt>Email</dt>
              <dd>{detail.email}</dd>
            </div>
            <div className="detail-row">
              <dt>Roll Number</dt>
              <dd>{detail.roll_number ?? "—"}</dd>
            </div>
            <div className="detail-row">
              <dt>Storage</dt>
              <dd>
                {formatBytes(detail.storage_used_bytes)} / {formatBytes(detail.storage_limit_bytes)}
              </dd>
            </div>
            <div className="detail-row">
              <dt>Files / Folders</dt>
              <dd>
                {detail.file_count} / {detail.folder_count}
              </dd>
            </div>
            <div className="detail-row">
              <dt>Websites</dt>
              <dd>{detail.websites.length}</dd>
            </div>
            <div className="detail-row">
              <dt>Created</dt>
              <dd>{formatDate(detail.created_at)}</dd>
            </div>
          </dl>

          {actionError && <p className="form-error">{actionError}</p>}

          {isSelf ? (
            <p className="section-loading">You cannot change your own role or disable your own account.</p>
          ) : (
            <div className="user-detail-actions">
              <label className="inline-field">
                Role
                <select
                  value={detail.role}
                  onChange={(e) => handleRoleChange(e.target.value as UserRole)}
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </label>

              <button
                type="button"
                className={detail.is_active ? "btn btn-danger-outline" : "btn btn-secondary"}
                onClick={handleActiveToggle}
              >
                {detail.is_active ? "Disable Account" : "Enable Account"}
              </button>
            </div>
          )}

          <h3 className="card-title">Websites</h3>
          {detail.websites.length === 0 ? (
            <EmptyState icon={<Globe size={24} />} title="No websites" description="This user hasn't deployed any websites." />
          ) : (
            <ul className="file-list">
              {detail.websites.map((w) => (
                <li key={w.id} className="file-row">
                  <span className="file-name">{w.name}</span>
                  <span className="file-actions">
                    <span className={w.status === "online" ? "status-ok" : "status-neutral"}>{w.status}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
