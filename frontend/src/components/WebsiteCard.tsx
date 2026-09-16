import { useState } from "react";
import {
  ExternalLink,
  Globe,
  MoreVertical,
  Play,
  RotateCw,
  ScrollText,
  Square,
  Trash2,
  X,
} from "lucide-react";

import type { Website } from "../api/websites";
import { StatusDot } from "./StatusDot";

const FRAMEWORK_LABEL: Record<Website["framework"], string> = {
  html: "Static HTML",
  react: "React / Vite",
  flask: "Dynamic — Flask",
  fastapi: "Dynamic — FastAPI",
  node: "Dynamic — Node.js",
};

// A deterministic (not random) color derived from the website's id,
// so a placeholder preview looks visually distinct per site without
// needing an actual screenshot/thumbnail-generation service.
function previewHue(seed: string): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) % 360;
  return hash;
}

interface WebsiteCardProps {
  site: Website;
  onDelete: (site: Website) => void;
  onStart: (site: Website) => void;
  onStop: (site: Website) => void;
  onRestart: (site: Website) => void;
  onShowLogs: (site: Website) => void;
  logsOpen: boolean;
  logsText: string;
  logsLoading: boolean;
  onCloseLogs: () => void;
}

export function WebsiteCard({
  site,
  onDelete,
  onStart,
  onStop,
  onRestart,
  onShowLogs,
  logsOpen,
  logsText,
  logsLoading,
  onCloseLogs,
}: WebsiteCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const isDynamic = site.type === "dynamic";
  const hue = previewHue(site.id);

  return (
    <div className="website-card">
      <div className="website-card-body">
        <div
          className="website-preview"
          style={{ background: `linear-gradient(135deg, hsl(${hue} 55% 24%), hsl(${hue} 45% 12%))` }}
        >
          <Globe size={22} className="website-preview-icon" />
        </div>

        <div className="website-card-info">
          <div className="website-card-top">
            <h4 className="website-card-name">{site.name}</h4>

            {isDynamic && (
              <div className="website-menu">
                <button
                  type="button"
                  className="icon-button"
                  aria-label="More actions"
                  onClick={() => setMenuOpen((v) => !v)}
                >
                  <MoreVertical size={16} />
                </button>
                {menuOpen && (
                  <div className="website-menu-dropdown" onMouseLeave={() => setMenuOpen(false)}>
                    {site.status === "online" && (
                      <button type="button" onClick={() => { setMenuOpen(false); onStop(site); }}>
                        <Square size={14} /> Stop
                      </button>
                    )}
                    {site.status === "stopped" && (
                      <button type="button" onClick={() => { setMenuOpen(false); onStart(site); }}>
                        <Play size={14} /> Start
                      </button>
                    )}
                    {(site.status === "online" || site.status === "stopped") && (
                      <button type="button" onClick={() => { setMenuOpen(false); onRestart(site); }}>
                        <RotateCw size={14} /> Restart
                      </button>
                    )}
                    <button type="button" onClick={() => { setMenuOpen(false); onShowLogs(site); }}>
                      <ScrollText size={14} /> Logs
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          <StatusDot status={site.status} />
          <div className="website-card-framework">{FRAMEWORK_LABEL[site.framework]}</div>

          {site.status === "online" && site.public_url && (
            <a href={site.public_url} target="_blank" rel="noreferrer" className="website-card-url">
              <ExternalLink size={12} /> {site.public_url}
            </a>
          )}

          {site.status === "failed" && site.error_message && (
            <p className="form-error website-card-error">{site.error_message}</p>
          )}

          <div className="website-card-date">
            Deployed on{" "}
            {new Date(site.created_at).toLocaleDateString(undefined, {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
          </div>
        </div>
      </div>

      <div className="website-card-actions">
        {site.status === "online" && site.public_url ? (
          <a href={site.public_url} target="_blank" rel="noreferrer" className="btn btn-secondary btn-block">
            <ExternalLink size={14} /> Open Website
          </a>
        ) : (
          <span className="btn btn-secondary btn-block btn-disabled">
            <ExternalLink size={14} /> Open Website
          </span>
        )}
        <button type="button" className="btn btn-danger-outline btn-block" onClick={() => onDelete(site)}>
          <Trash2 size={14} /> Delete
        </button>
      </div>

      {logsOpen && (
        <div className="logs-panel">
          <div className="logs-panel-header">
            <strong>Logs</strong>
            <button type="button" className="icon-button" onClick={onCloseLogs} aria-label="Close logs">
              <X size={16} />
            </button>
          </div>
          <pre className="logs-panel-body">{logsLoading ? "Loading..." : logsText || "(no logs)"}</pre>
        </div>
      )}
    </div>
  );
}
