import { useState } from "react";

import { ThemeToggle } from "./components/ThemeToggle";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { AdminApp } from "./pages/AdminApp";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";

type View = "login" | "register";

function AppContent() {
  const { user, isLoading } = useAuth();
  const [view, setView] = useState<View>("login");

  if (isLoading) {
    return (
      <div className="auth-page">
        <p>Loading...</p>
      </div>
    );
  }

  if (user) {
    // The backend is the real authority here (every /api/admin/*
    // route independently enforces role === admin) -- this branch is
    // only about which UI to render, never a security boundary on its
    // own. See docs/ADMIN-DASHBOARD.md.
    return user.role === "admin" ? <AdminApp /> : <Dashboard />;
  }

  return (
    <div className="auth-page">
      <div className="auth-page-toggle">
        <ThemeToggle />
      </div>
      {view === "login" ? (
        <Login onSwitchToRegister={() => setView("register")} />
      ) : (
        <Register onSwitchToLogin={() => setView("login")} />
      )}
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
