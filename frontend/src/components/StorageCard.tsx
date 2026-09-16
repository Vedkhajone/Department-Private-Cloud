import { useEffect, useState } from "react";
import { Cloud } from "lucide-react";

import { getStorageUsage, type StorageUsage } from "../api/storage";
import { useAuth } from "../context/AuthContext";

function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 MB";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, exponent);
  return `${value.toFixed(exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

export function StorageCard() {
  const { token } = useAuth();
  const [usage, setUsage] = useState<StorageUsage | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    getStorageUsage(token)
      .then((data) => {
        if (!cancelled) setUsage(data);
      })
      .catch(() => {
        /* the bar simply stays empty if this fails -- non-critical */
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const percent = usage ? Math.min(100, (usage.used_bytes / usage.quota_bytes) * 100) : 0;

  return (
    <div className="card storage-card">
      <div className="storage-card-header">
        <div className="storage-card-title">
          <Cloud size={18} />
          <span>Storage Usage</span>
        </div>
        {usage && (
          <span className="storage-card-figures">
            {formatBytes(usage.used_bytes)} of {formatBytes(usage.quota_bytes)}
          </span>
        )}
      </div>

      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${percent}%` }} />
      </div>

      {usage && (
        <div className="storage-card-footer">
          <span>{percent.toFixed(0)}% used</span>
          <span>{formatBytes(usage.available_bytes)} free</span>
        </div>
      )}
    </div>
  );
}
