import { useState } from "react";

import { ThemeToggle } from "./components/ThemeToggle";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
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
    return <Dashboard />;
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
