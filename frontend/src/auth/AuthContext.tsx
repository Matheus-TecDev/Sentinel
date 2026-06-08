import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import { apiRequest } from "../api/client";
import type { User } from "../types";

interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

interface AuthContextValue {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  canManageServices: boolean;
  canManageUsers: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredUser(): User | null {
  const raw = localStorage.getItem("sentinel_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    localStorage.removeItem("sentinel_user");
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("sentinel_token"));
  const [user, setUser] = useState<User | null>(() => readStoredUser());

  async function login(email: string, password: string): Promise<void> {
    const response = await apiRequest<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    setToken(response.access_token);
    setUser(response.user);
    localStorage.setItem("sentinel_token", response.access_token);
    localStorage.setItem("sentinel_user", JSON.stringify(response.user));
  }

  function logout(): void {
    setToken(null);
    setUser(null);
    localStorage.removeItem("sentinel_token");
    localStorage.removeItem("sentinel_user");
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
      canManageServices: user?.role === "ADMIN" || user?.role === "OPERATOR",
      canManageUsers: user?.role === "ADMIN"
    }),
    [token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
