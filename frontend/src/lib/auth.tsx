import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, tokenStore } from "./api";

export interface Me {
  id: string;
  email: string;
  full_name: string;
  organization_id: string;
  roles: string[];
  permissions: string[];
}

interface AuthState {
  me: Me | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  can: (permission: string) => boolean;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadMe() {
    if (!tokenStore.access) {
      setLoading(false);
      return;
    }
    try {
      setMe(await api.get<Me>("/auth/me"));
    } catch {
      tokenStore.clear();
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMe();
  }, []);

  async function login(email: string, password: string) {
    const res = await api.post<{ access_token: string; refresh_token: string }>("/auth/login", {
      email,
      password,
    });
    tokenStore.set(res.access_token, res.refresh_token);
    setMe(await api.get<Me>("/auth/me"));
  }

  function logout() {
    tokenStore.clear();
    setMe(null);
  }

  const can = (permission: string) =>
    !!me && (me.permissions.includes("platform:admin") || me.permissions.includes(permission));

  return (
    <AuthContext.Provider value={{ me, loading, login, logout, can }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
