import { Settings as SettingsIcon } from "lucide-react";

import { EmptyState } from "../components/EmptyState";

/**
 * Placeholder -- DECP doesn't have user-configurable settings yet.
 * Shown honestly as "coming soon" rather than wiring up controls that
 * don't do anything.
 */
export function Settings() {
  return (
    <div className="card section-card">
      <div className="section-header">
        <div className="section-header-title">
          <span className="section-icon accent-blue">
            <SettingsIcon size={18} />
          </span>
          <div>
            <h3>Settings</h3>
            <p>Account and application preferences</p>
          </div>
        </div>
      </div>

      <EmptyState
        icon={<SettingsIcon size={28} />}
        title="Settings are coming soon"
        description="Account preferences will appear here in a future update."
      />
    </div>
  );
}
