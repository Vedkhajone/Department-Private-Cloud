import { useEffect, useState } from "react";

import type { User } from "../api/auth";
import { listWebsites } from "../api/websites";
import { useAuth } from "../context/AuthContext";

function initial(name: string): string {
  return (name.trim()[0] || "?").toUpperCase();
}

function formatStorageLimit(mb: number): string {
  if (mb >= 1024 && mb % 1024 === 0) return `${(mb / 1024).toFixed(1)} GB`;
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB (${mb} MB)`;
  return `${mb} MB`;
}

export function AccountCard({ user }: { user: User }) {
  const { token } = useAuth();
  const [websiteCount, setWebsiteCount] = useState<number | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    listWebsites(token)
      .then((list) => {
        if (!cancelled) setWebsiteCount(list.length);
      })
      .catch(() => {
        /* non-critical -- the row is simply omitted below */
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="card account-card">
      <div className="account-card-header">
        <span className="avatar avatar-neutral">{initial(user.name)}</span>
        <span className="badge">{user.role}</span>
      </div>

      <h3 className="card-title">Your Account</h3>

      <dl className="detail-list">
        <div className="detail-row">
          <dt>Email</dt>
          <dd>{user.email}</dd>
        </div>
        <div className="detail-row">
          <dt>Roll Number</dt>
          <dd>{user.roll_number ?? "—"}</dd>
        </div>
        <div className="detail-row">
          <dt>Storage Limit</dt>
          <dd>{formatStorageLimit(user.storage_limit)}</dd>
        </div>
        {websiteCount !== null && (
          <div className="detail-row">
            <dt>Websites Deployed</dt>
            <dd>{websiteCount}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}
