import { useCallback, useEffect, useState } from "react";
import { Search, Users } from "lucide-react";

import { listUsers, type AdminUserSummary } from "../../api/admin";
import type { UserRole } from "../../api/auth";
import { ApiError } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { useAuth } from "../../context/AuthContext";
import { formatBytes, formatDate } from "../../utils/format";

const ROLE_BADGE: Record<UserRole, string> = {
  student: "badge",
  faculty: "badge badge-green",
  admin: "badge badge-blue",
};

export function AdminUsers({ onOpenUser }: { onOpenUser: (userId: number) => void }) {
  const { token } = useAuth();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<AdminUserSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const pageSize = 25;

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const load = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await listUsers(token, debouncedSearch, page, pageSize);
      setItems(result.items);
      setTotal(result.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load users");
    } finally {
      setIsLoading(false);
    }
  }, [token, debouncedSearch, page]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="card section-card">
      <div className="section-header">
        <div className="section-header-title">
          <span className="section-icon accent-blue">
            <Users size={18} />
          </span>
          <div>
            <h3>Users</h3>
            <p>{total} registered accounts</p>
          </div>
        </div>
      </div>

      <div className="search-bar">
        <Search size={15} />
        <input
          type="text"
          placeholder="Search users..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {error && <p className="form-error">{error}</p>}

      {isLoading ? (
        <p className="section-loading">Loading...</p>
      ) : items.length === 0 ? (
        <EmptyState icon={<Users size={28} />} title="No users found" description="Try a different search." />
      ) : (
        <>
          <div className="table-scroll">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Storage</th>
                  <th>Websites</th>
                  <th>Joined</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {items.map((u) => (
                  <tr key={u.id} onClick={() => onOpenUser(u.id)} className="table-row-clickable">
                    <td>{u.name}</td>
                    <td>{u.email}</td>
                    <td>
                      <span className={ROLE_BADGE[u.role]}>{u.role}</span>
                    </td>
                    <td>
                      {formatBytes(u.storage_used_bytes)} / {formatBytes(u.storage_limit_bytes)}
                    </td>
                    <td>{u.website_count}</td>
                    <td>{formatDate(u.created_at)}</td>
                    <td>
                      <span className={u.is_active ? "status-ok" : "status-bad"}>
                        {u.is_active ? "Active" : "Disabled"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                type="button"
                className="btn btn-secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </button>
              <span>
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
