import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import AdminSystemHealthPage from "@/app/admin/system-health/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { monitoringService } from "@/lib/api/services/monitoring.service";
import { useDemoStore } from "@/store/useDemoStore";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/admin/system-health",
}));

vi.mock("@/lib/api/services/monitoring.service", () => ({
  monitoringService: {
    getDetailedHealth: vi.fn(),
  },
}));

describe("Phase 8D - Admin System Health & Diagnostic Probes", () => {
  let queryClient: QueryClient;

  const mockDetailedHealth = {
    status: "ready",
    service: "sentinelai",
    version: "0.1.0",
    uptime_seconds: 7200,
    components: {
      database: {
        status: "connected",
        latency_ms: 1.85,
      },
      redis: {
        status: "connected",
      },
    },
    ecapa_engine: {
      model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
      loaded: true,
      device: "cpu",
      embedding_dim: 192,
    },
    biometric_storage: {
      accessible: true,
      storage_root: "storage/biometrics",
    },
    encryption_service: {
      configured: true,
      algorithm: "AES-256-GCM",
    },
    timestamp: "2026-11-13T12:00:00Z",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    useDemoStore.setState({ isDemoMode: false });
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    (monitoringService.getDetailedHealth as any).mockResolvedValue(mockDetailedHealth);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AdminSystemHealthPage />
      </QueryClientProvider>
    );

  it("renders cluster status and core subsystem health indicators", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("sentinelai")).toBeInTheDocument();
      expect(screen.getByText("PostgreSQL 18 DB")).toBeInTheDocument();
      expect(screen.getByText("1.85 ms")).toBeInTheDocument();
      expect(screen.getByText("Redis Rate Limiter")).toBeInTheDocument();
      expect(screen.getByText("ECAPA-TDNN Engine")).toBeInTheDocument();
      expect(screen.getByText("Biometric Vault")).toBeInTheDocument();
      expect(screen.getByText("Envelope Encryption")).toBeInTheDocument();
    });
  });

  it("triggers health probe refetch when clicking Poll Health Probes", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("sentinelai")).toBeInTheDocument();
    });

    const pollBtn = screen.getByRole("button", { name: /Poll Health Probes/i });
    fireEvent.click(pollBtn);

    await waitFor(() => {
      expect(monitoringService.getDetailedHealth).toHaveBeenCalledTimes(2);
    });
  });
});
