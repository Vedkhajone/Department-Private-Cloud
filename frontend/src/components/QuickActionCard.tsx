import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";

interface QuickActionCardProps {
  icon: ReactNode;
  title: string;
  description: string;
  accent: "blue" | "green";
  onClick: () => void;
}

export function QuickActionCard({ icon, title, description, accent, onClick }: QuickActionCardProps) {
  return (
    <button type="button" className={`quick-action-card accent-${accent}`} onClick={onClick}>
      <span className="quick-action-icon">{icon}</span>
      <span className="quick-action-body">
        <span className="quick-action-title">{title}</span>
        <span className="quick-action-description">{description}</span>
      </span>
      <ChevronRight size={18} className="quick-action-arrow" />
    </button>
  );
}
