import { useState, type FormEvent } from "react";
import { X } from "lucide-react";

import { ApiError } from "../api/client";
import { deployWebsite } from "../api/websites";
import { useAuth } from "../context/AuthContext";

interface DeployWebsiteModalProps {
  onClose: () => void;
  onDeployed: () => Promise<void> | void;
}

/**
 * Visual redesign of the existing deploy form as a modal dialog. The
 * deployment logic/validation/API call underneath is unchanged from
 * the inline form it replaces -- only the presentation moved.
 */
export function DeployWebsiteModal({ onClose, onDeployed }: DeployWebsiteModalProps) {
  const { token } = useAuth();
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isDeploying, setIsDeploying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token || !file) return;
    setIsDeploying(true);
    setError(null);
    try {
      await deployWebsite(token, name, file);
      await onDeployed();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Deployment failed");
    } finally {
      setIsDeploying(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Deploy Website</h3>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <label>
            Website Name
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Portfolio"
              required
            />
          </label>

          <label>
            Website ZIP
            <input
              type="file"
              accept=".zip"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              required
            />
          </label>

          {error && <p className="form-error">{error}</p>}

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={isDeploying || !file}>
              {isDeploying ? "Deploying..." : "Deploy Website"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
