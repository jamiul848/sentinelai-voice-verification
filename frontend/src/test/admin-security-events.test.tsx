import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import AdminSecurityEventsPage from "@/app/admin/security-events/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { adminService } from "@/lib/api/services/admin.service";
import { useDemoStore } from "@/store/useDemoStore";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/admin/security-events",
}));

vi.mock("@/lib/api/services/admin.service", () => ({
  adminService: {
    getSecurityEvents: vi.fn(),
  },
}));

describe("Phase 8D - Admin Security Events & Abuse Defense Page", () => {
  let queryClient: QueryClient;

  const mockSecurityData = {
    rate_limiter: {
      backend: "redis",
      redis_configured: true,
      rules: {
        auth_login: "5 per minute",
        auth_register: "3 per hour",
        biometrics_enroll: "10 per hour",
        biometrics_verify: "30 per minute",
      },
    },
    events: [
      {
        id: "sec-001",
        action: "AUTH_LOGIN_FAILED",
        resource_type: "auth",
        resource_id: "sec-incident-01",
        actor_email: "unknown_attacker@domain.com",
        payload: { ip: "198.51.100.42", attempts: 5 },
        created_at: "2026-11-13T12:00:00Z",
      },
      {
        id: "sec-002",
        action: "RATE_LIMIT_TRIGGERED",
        resource_type: "rate_limiter",
        resource_id: "sec-incident-02",
        actor_email: "flooder@domain.com",
        payload: { endpoint: "/api/v1/auth/login", status: 429 },
        created_at: "2026-11-13T12:05:00Z",
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    useDemoStore.setState({ isDemoMode: false });
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    (adminService.getSecurityEvents as any).mockResolvedValue(mockSecurityData);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AdminSecurityEventsPage />
      </QueryClientProvider>
    );

  it("renders rate limiter configuration and security incident ledger", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("Rate Limiter Backend")).toBeInTheDocument();
      expect(screen.getByText("REDIS")).toBeInTheDocument();
      expect(screen.getByText("Authentication Quotas")).toBeInTheDocument();
      expect(screen.getByText("Biometric Endpoint Quotas")).toBeInTheDocument();
      expect(screen.getByText("AUTH_LOGIN_FAILED")).toBeInTheDocument();
      expect(screen.getByText("RATE_LIMIT_TRIGGERED")).toBeInTheDocument();
      expect(screen.getByText("unknown_attacker@domain.com")).toBeInTheDocument();
    });
  });
});

