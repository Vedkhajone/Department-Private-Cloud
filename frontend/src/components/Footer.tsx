export function Footer() {
  return (
    <footer className="app-footer">
      <div>
        <div className="app-footer-title">Department Engineering Cloud</div>
        <div className="app-footer-subtitle">Empowering Students. Building the Future.</div>
      </div>
      <div className="app-footer-meta">
        <span className="badge">v{import.meta.env.VITE_APP_VERSION}</span>
        <span>Made with ♥ for the Department</span>
      </div>
    </footer>
  );
}
