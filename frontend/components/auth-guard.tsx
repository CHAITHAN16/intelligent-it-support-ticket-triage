"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/lib/auth";
import type { AuthRole } from "@/lib/api";

function homeForRole(role: AuthRole): string {
  if (role === "AGENT") return "/agent";
  if (role === "EMPLOYEE") return "/tickets";
  return "/";
}

export function AuthGuard({ allowedRoles, children }: { allowedRoles: AuthRole[]; children: React.ReactNode }) {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (!allowedRoles.includes(user.role)) router.replace(homeForRole(user.role));
  }, [allowedRoles, isLoading, router, user]);

  if (isLoading || !user || !allowedRoles.includes(user.role)) {
    return <div className="flex min-h-screen items-center justify-center bg-[#f6f8fb] px-6 text-sm text-slate-500">Checking your access...</div>;
  }

  return children;
}
