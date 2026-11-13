import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import AdminDashboardPage from "@/app/admin/dashboard/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { adminService } from "@/lib/api/services/admin.service";
import { useDemoStore } from "@/store/useDemoStore";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/admin/dashboard",
}));

vi.mock("@/lib/api/services/admin.service", () => ({
  adminService: {
    getOverview: vi.fn(),
    getAnalytics: vi.fn(),
    getAuditLogs: vi.fn(),
  },
}));

// Mock ResponsiveContainer for recharts
vi.mock("recharts", async () => {
  const original = await vi.importActual("recharts");
  return {
    ...original,
    ResponsiveContainer: ({ children }: any) => <div data-testid="recharts-container">{children}</div>,
  };
});

describe("Phase 8D - Admin Dashboard Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    useDemoStore.setState({ isDemoMode: false });
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    (adminService.getOverview as any).mockResolvedValue({
      users: {
        total: 142,
        active: 138,
        inactive: 4,
      },
      voice_profiles: {
        total: 104,
        active: 96,
        revoked: 8,
      },
      verifications: {
        total: 1250,
        matches: 1180,
        no_matches: 70,
        match_rate: 94.4,
        avg_latency_ms: 118.4,
      },
      system_health: {
        status: "ready",
        uptime_seconds: 7200,
        database_status: "connected",
        redis_status: "connected",
        model_loaded: true,
        encryption_configured: true,
      },
      recent_audit_events: [
        {
          id: "log-1",
          action: "AUTH_LOGIN_SUCCESS",
          resource_type: "auth",
          resource_id: "usr-1",
          actor_user_id: "usr-1",
          created_at: "2026-11-13T12:00:00Z",
        },
      ],
    });

    (adminService.getAnalytics as any).mockResolvedValue({
      time_window_days: 7,
      total_verifications: 1250,
      matches: 1180,
      no_matches: 70,
      match_rate: 0.944,
      avg_latency_ms: 118.4,
      timeline: [
        { date: "2026-11-12", matches: 45, no_matches: 3 },
        { date: "2026-11-13", matches: 60, no_matches: 2 },
      ],
    });

    (adminService.getAuditLogs as any).mockResolvedValue({
      items: [
        {
          id: "log-1",
          action: "AUTH_LOGIN_SUCCESS",
          user_id: "usr-1",
          ip_address: "127.0.0.1",
          timestamp: "2026-11-13T12:00:00Z",
        },
      ],
      total: 1,
      limit: 10,
      offset: 0,
    });
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AdminDashboardPage />
      </QueryClientProvider>
    );

  it("renders 8 platform statistic cards with backend data", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("142")).toBeInTheDocument(); // Total Users
      expect(screen.getByText("138")).toBeInTheDocument(); // Active Users
      expect(screen.getByText("4")).toBeInTheDocument(); // Inactive Users
      expect(screen.getByText("96")).toBeInTheDocument(); // Biometric Profiles
      expect(screen.getByText("8")).toBeInTheDocument(); // Shredded
      expect(screen.getByText("1250")).toBeInTheDocument(); // Total Verifications
      expect(screen.getByText("1180")).toBeInTheDocument(); // Matches
      expect(screen.getByText("70")).toBeInTheDocument(); // Rejections
    });
  });

  it("renders cluster health subsystem status cards", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("Cluster Subsystems")).toBeInTheDocument();
      expect(screen.getByText("PostgreSQL 18 DB")).toBeInTheDocument();
      expect(screen.getByText("Redis Rate Limiter")).toBeInTheDocument();
      expect(screen.getByText("ECAPA-TDNN PyTorch")).toBeInTheDocument();
      expect(screen.getByText("AES-256-GCM Vault")).toBeInTheDocument();
    });
  });

  it("renders recent audit stream items", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("System Audit Log Stream")).toBeInTheDocument();
      expect(screen.getByText("AUTH_LOGIN_SUCCESS")).toBeInTheDocument();
    });
  });
});
