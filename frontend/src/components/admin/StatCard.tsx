import type { ReactNode } from "react";

interface StatCardProps {
  icon: ReactNode;
  label: string;
  value: string;
  sublabel?: string;
  accent?: "blue" | "green" | "amber" | "red";
}

export function StatCard({ icon, label, value, sublabel, accent = "blue" }: StatCardProps) {
  return (
    <div className="card stat-card">
      <div className="stat-card-top">
        <span className={`stat-card-icon accent-${accent}`}>{icon}</span>
        <span className="stat-card-label">{label}</span>
      </div>
      <div className="stat-card-value">{value}</div>
      {sublabel && <div className="stat-card-sublabel">{sublabel}</div>}
    </div>
  );
}
