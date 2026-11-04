"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { api, getToken, setToken, setUnauthorizedHandler, subscribeToken } from "./api";

type AuthState = {
  /** "loading" until the browser has been read, then "authed" or "anon". */
  status: "loading" | "authed" | "anon";
  email: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const token = useSyncExternalStore(subscribeToken, getToken, () => undefined);
  const [emailByToken, setEmailByToken] = useState<{ token: string; email: string } | null>(null);

  useEffect(() => {
    setUnauthorizedHandler(() => router.replace("/login"));
    return () => setUnauthorizedHandler(null);
  }, [router]);

  useEffect(() => {
    if (!token) return;
    let active = true;
    api
      .me()
      .then((u) => active && setEmailByToken({ token, email: u.email }))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [token]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password);
    setToken(res.access_token);
    setEmailByToken({ token: res.access_token, email });
  }, []);

  const signup = useCallback(
    async (email: string, password: string) => {
      await api.register(email, password);
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(() => {
    setToken(null);
    router.replace("/login");
  }, [router]);

  const value = useMemo<AuthState>(
    () => ({
      status: token === undefined ? "loading" : token ? "authed" : "anon",
      email: token && emailByToken?.token === token ? emailByToken.email : null,
      login,
      signup,
      logout,
    }),
    [token, emailByToken, login, signup, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
