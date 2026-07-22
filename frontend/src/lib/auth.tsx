import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, tokenStore } from "./api";

export interface Me {
  id: string;
  email: string;
  full_name: string;
  organization_id: string;
  home_organization_id: string;
  branch_id: string | null;
  applicant_id: string | null;
  roles: string[];
  permissions: string[];
}

interface AuthState {
  me: Me | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<string | null>;
  verifyMfa: (challengeToken: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  can: (permission: string) => boolean;
  switchOrganization: (organizationId: string) => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadMe() {
    try {
      if (!tokenStore.access && !(await api.refreshSession())) return;
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
    const res = await api.post<{
      access_token: string | null;
      mfa_required: boolean;
      challenge_token: string | null;
    }>("/auth/login", {
      email,
      password,
    });
    if (res.mfa_required && res.challenge_token) return res.challenge_token;
    if (!res.access_token) throw new Error("Authentication response did not include a session");
    tokenStore.set(res.access_token);
    setMe(await api.get<Me>("/auth/me"));
    return null;
  }

  async function verifyMfa(challengeToken: string, code: string) {
    const res = await api.post<{ access_token: string }>("/auth/mfa/verify", {
      challenge_token: challengeToken,
      code,
    });
    tokenStore.set(res.access_token);
    setMe(await api.get<Me>("/auth/me"));
  }

  async function logout() {
    await api.logout();
    queryClient.clear();
    setMe(null);
  }

  async function switchOrganization(organizationId: string) {
    const response = await api.post<{ access_token: string }>("/auth/switch-organization", {
      organization_id: organizationId,
    });
    tokenStore.set(response.access_token);
    queryClient.clear();
    setMe(await api.get<Me>("/auth/me"));
  }

  const can = (permission: string) =>
    !!me && (me.permissions.includes("platform:admin") || me.permissions.includes(permission));

  return (
    <AuthContext.Provider value={{ me, loading, login, verifyMfa, logout, can, switchOrganization }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
