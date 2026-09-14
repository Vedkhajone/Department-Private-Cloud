import { useAuth } from "../context/AuthContext";
import { Files } from "./Files";

export function Dashboard() {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <>
      <div className="dashboard-card">
        <h1>Department Engineering Cloud</h1>
        <p className="welcome">Welcome, {user.name}</p>

        <div className="status-row">
          <span>Email</span>
          <span>{user.email}</span>
        </div>
        <div className="status-row">
          <span>Roll Number</span>
          <span>{user.roll_number ?? "—"}</span>
        </div>
        <div className="status-row">
          <span>Role</span>
          <span>{user.role}</span>
        </div>
        <div className="status-row">
          <span>Storage Limit</span>
          <span>{user.storage_limit} MB</span>
        </div>

        <button type="button" onClick={logout}>
          Logout
        </button>
      </div>

      <Files />
    </>
  );
}
