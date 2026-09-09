"use client";

import { useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";

import {
  clearAccessToken,
  getAccessToken,
  getCurrentUser,
  login as loginRequest,
  storeAccessToken,
  type AuthRole,
  type AuthUser,
} from "@/lib/api";

type AuthContextValue = {
  user: AuthUser | null;
  role: AuthRole | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const token = getAccessToken();

    async function restoreSession() {
      if (!token) {
        if (active) setIsLoading(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser();
        if (active) setUser(currentUser);
      } catch {
        clearAccessToken();
        if (active) setUser(null);
      } finally {
        if (active) setIsLoading(false);
      }
    }

    void restoreSession();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    function handleUnauthorized() {
      clearAccessToken();
      setUser(null);
      router.replace("/login");
    }

    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, [router]);

  async function login(email: string, password: string): Promise<AuthUser> {
    const response = await loginRequest(email, password);
    storeAccessToken(response.access_token);
    const currentUser = await getCurrentUser();
    setUser(currentUser);
    return currentUser;
  }

  function logout() {
    clearAccessToken();
    setUser(null);
    router.replace("/login");
  }

  const value = { user, role: user?.role ?? null, isLoading, login, logout };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
