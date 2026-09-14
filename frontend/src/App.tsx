import { useState } from "react";

import { AuthProvider, useAuth } from "./context/AuthContext";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";

type View = "login" | "register";

function AppContent() {
  const { user, isLoading } = useAuth();
  const [view, setView] = useState<View>("login");

  if (isLoading) {
    return (
      <div className="app">
        <p>Loading...</p>
      </div>
    );
  }

  if (user) {
    return (
      <div className="app app-wide">
        <Dashboard />
      </div>
    );
  }

  return (
    <div className="app">
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
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
