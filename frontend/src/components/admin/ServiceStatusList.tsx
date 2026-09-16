import type { ServiceStatus } from "../../api/admin";

export function ServiceStatusList({ services }: { services: ServiceStatus[] }) {
  return (
    <ul className="service-status-list">
      {services.map((s) => (
        <li key={s.name} className="service-status-row">
          <span className={`status-dot ${s.status === "healthy" ? "status-dot-online" : "status-dot-failed"}`}>
            <span className="status-dot-marker" aria-hidden="true" />
            {s.name}
          </span>
          <span className={s.status === "healthy" ? "status-ok" : "status-bad"}>
            {s.status === "healthy" ? "Healthy" : "Unavailable"}
          </span>
        </li>
      ))}
    </ul>
  );
}
