"use client";

import React, { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";
import { Shield } from "lucide-react";

interface RouteGuardProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export function RouteGuard({ children, requireAdmin = false }: RouteGuardProps) {
  const { isAuthenticated, isLoading, user } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || isLoading) return;

    if (!isAuthenticated) {
      const redirectPath = encodeURIComponent(pathname);
      router.replace(`/login?redirect=${redirectPath}`);
      return;
    }

    if (requireAdmin) {
      const hasAdminRole = user?.roles?.some(
        (role) => role === "ADMIN" || role === "SUPER_ADMIN"
      );
      if (!hasAdminRole) {
        router.replace("/dashboard");
      }
    }
  }, [mounted, isAuthenticated, isLoading, user, requireAdmin, router, pathname]);

  if (!mounted || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-400">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 animate-pulse">
            <Shield className="w-6 h-6" />
          </div>
          <p className="text-xs uppercase tracking-wider font-mono">Authenticating Sentinel Session...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (requireAdmin) {
    const hasAdminRole = user?.roles?.some(
      (role) => role === "ADMIN" || role === "SUPER_ADMIN"
    );
    if (!hasAdminRole) {
      return null;
    }
  }

  return <>{children}</>;
}

