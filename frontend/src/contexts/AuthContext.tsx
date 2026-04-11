import React, { useState, useEffect, useCallback, useRef } from "react";
import { getCurrentUser, login as apiLogin, logout as apiLogout } from "../services/api";
import { AuthContext, type AuthUser } from "./authContextDef";

export { AuthContext } from "./authContextDef";
export type { AuthUser } from "./authContextDef";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Held so that login() can abort the in-flight initial probe, preventing a
  // stale 401 from that probe triggering the global interceptor redirect after
  // the user has already successfully authenticated.
  const initAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    initAbortRef.current = controller;

    const load = async () => {
      try {
        const data = await getCurrentUser(controller.signal);
        if (!controller.signal.aborted) setUser(data);
      } catch {
        if (!controller.signal.aborted) setUser(null);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    load();
    return () => { controller.abort(); };
  }, []);

  const refresh = useCallback(async () => {
    try {
      const data = await getCurrentUser();
      setUser(data);
    } catch {
      setUser(null);
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    // Cancel the initial auth probe so its eventual 401 cannot trigger a
    // redirect after we have already established a session via login.
    initAbortRef.current?.abort();
    const data = await apiLogin(username, password);
    setUser(data);
    setLoading(false);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refresh, isAdmin: user?.role === "admin" }}>
      {children}
    </AuthContext.Provider>
  );
}
