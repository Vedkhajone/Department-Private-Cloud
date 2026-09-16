import type { WebsiteStatus } from "../api/websites";

const STATUS_LABEL: Record<WebsiteStatus, string> = {
  pending: "Pending",
  building: "Building",
  online: "Online",
  stopped: "Stopped",
  failed: "Failed",
  deleting: "Deleting",
};

const STATUS_CLASS: Record<WebsiteStatus, string> = {
  pending: "status-dot-neutral",
  building: "status-dot-building",
  online: "status-dot-online",
  stopped: "status-dot-neutral",
  failed: "status-dot-failed",
  deleting: "status-dot-neutral",
};

export function StatusDot({ status }: { status: WebsiteStatus }) {
  return (
    <span className={`status-dot ${STATUS_CLASS[status]}`}>
      <span className="status-dot-marker" aria-hidden="true" />
      {STATUS_LABEL[status]}
    </span>
  );
}
