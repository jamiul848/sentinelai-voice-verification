"use client";

import React, { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/useAuthStore";
import { useRouter } from "next/navigation";

export function AppProviders({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000,
            retry: (failureCount, error: any) => {
              // Don't retry on 401, 403, or 404
              if (error?.status === 401 || error?.status === 403 || error?.status === 404) {
                return false;
              }
              return failureCount < 2;
            },
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  const initializeAuth = useAuthStore((s) => s.initialize);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const router = useRouter();

  useEffect(() => {
    initializeAuth();

    const handleLogout = () => {
      clearAuth();
      router.push("/login");
    };

    window.addEventListener("sentinel:logout", handleLogout);
    return () => {
      window.removeEventListener("sentinel:logout", handleLogout);
    };
  }, [initializeAuth, clearAuth, router]);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

