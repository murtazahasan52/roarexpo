import { createContext, useContext, useEffect, useState } from "react";

const STORAGE_KEY = "roar_expo_admin_session";

export const AdminAuthContext = createContext(null);

export function useAdminAuthProviderValue() {
  const [session, setSession] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setSession(JSON.parse(raw));
    } catch (e) {
      // ignore malformed/blocked storage
    } finally {
      setReady(true);
    }
  }, []);

  function login(token, admin) {
    const next = { token, admin };
    setSession(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch (e) {
      // storage unavailable — session still works for this tab via state
    }
  }

  function logout() {
    setSession(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      // ignore
    }
  }

  return { session, ready, login, logout };
}

export function useAdminAuth() {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) throw new Error("useAdminAuth must be used within AdminAuthContext.Provider");
  return ctx;
}
