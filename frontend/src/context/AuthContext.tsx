import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { fetchCurrentUser, login as apiLogin } from "../api/auth";
import type { LoginPayload, User } from "../api/auth";

const TOKEN_STORAGE_KEY = "decp_access_token";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Holds authentication state for the whole app: the current token and
 * user, backed by localStorage so a page refresh doesn't log the user
 * out. This is a reasonable approach for this development stage --
 * a production deployment may want httpOnly cookies instead.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    try {
      return localStorage.getItem(TOKEN_STORAGE_KEY);
    } catch {
      return null;
    }
  });
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On load (or whenever the token changes), fetch the authenticated
  // user so a refresh restores the dashboard instead of bouncing back
  // to the login page.
  useEffect(() => {
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    fetchCurrentUser(token)
      .then((fetchedUser) => {
        if (!cancelled) setUser(fetchedUser);
      })
      .catch(() => {
        // Token is invalid/expired -- clear it and fall back to login.
        if (!cancelled) {
          setUser(null);
          setToken(null);
          try {
            localStorage.removeItem(TOKEN_STORAGE_KEY);
          } catch {
            /* ignore */
          }
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  async function login(payload: LoginPayload) {
    const result = await apiLogin(payload);
    setUser(result.user);
    setToken(result.access_token);
    try {
      localStorage.setItem(TOKEN_STORAGE_KEY, result.access_token);
    } catch {
      /* localStorage unavailable -- auth still works for this session */
    }
  }

  function logout() {
    setUser(null);
    setToken(null);
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
