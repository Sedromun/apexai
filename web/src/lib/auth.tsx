"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch, postAuth, setAccessToken } from "./api";
import type { Account } from "./types";

type AuthStatus = "loading" | "authed" | "anon";

interface AuthContextValue {
  user: Account | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Account | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  const loadUser = useCallback(async () => {
    const me = await apiFetch<Account>("/me");
    setUser(me);
    setStatus("authed");
  }, []);

  // On mount: try to restore the session from the httpOnly refresh cookie.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const res = await fetch("/api/auth/refresh", { method: "POST" });
      if (!res.ok) {
        if (!cancelled) setStatus("anon");
        return;
      }
      const data = (await res.json()) as { access_token: string };
      setAccessToken(data.access_token);
      try {
        if (!cancelled) await loadUser();
      } catch {
        if (!cancelled) setStatus("anon");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadUser]);

  const finishAuth = useCallback(
    async (tokens: { access_token: string }) => {
      setAccessToken(tokens.access_token);
      await loadUser();
    },
    [loadUser],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      await finishAuth(await postAuth("/api/auth/login", { email, password }));
    },
    [finishAuth],
  );

  const register = useCallback(
    async (email: string, password: string) => {
      await finishAuth(await postAuth("/api/auth/register", { email, password }));
    },
    [finishAuth],
  );

  const logout = useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    setAccessToken(null);
    setUser(null);
    setStatus("anon");
  }, []);

  const refreshUser = useCallback(async () => {
    await loadUser();
  }, [loadUser]);

  return (
    <AuthContext.Provider value={{ user, status, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
