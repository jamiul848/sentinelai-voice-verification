import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import AdminAnalyticsPage from "@/app/admin/analytics/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { adminService } from "@/lib/api/services/admin.service";
import { useDemoStore } from "@/store/useDemoStore";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/admin/analytics",
}));

vi.mock("@/lib/api/services/admin.service", () => ({
  adminService: {
    getAnalytics: vi.fn(),
  },
}));

vi.mock("recharts", async () => {
  const original = await vi.importActual("recharts");
  return {
    ...original,
    ResponsiveContainer: ({ children }: any) => <div data-testid="recharts-container">{children}</div>,
  };
});

describe("Phase 8D - Admin Analytics & Performance Page", () => {
  let queryClient: QueryClient;

  const mockAnalytics = {
    total_verifications: 540,
    matches: 512,
    no_matches: 28,
    match_rate: 94.8,
    no_match_rate: 5.2,
    average_latency_ms: 124.6,
    timeline: [
      { date: "2026-11-12", matches: 200, no_matches: 10, total: 210, avg_latency_ms: 120 },
      { date: "2026-11-13", matches: 312, no_matches: 18, total: 330, avg_latency_ms: 128 },
    ],
    active_threshold: {
      version_tag: "v1.0.0-baseline",
      threshold_value: 0.405898,
      calibration_dataset: "LibriSpeech dev-clean",
      calibration_criterion: "equal_error_rate_minimization",
      model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    useDemoStore.setState({ isDemoMode: false });
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    (adminService.getAnalytics as any).mockResolvedValue(mockAnalytics);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AdminAnalyticsPage />
      </QueryClientProvider>
    );

  it("renders biometric verification performance metrics", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("540")).toBeInTheDocument(); // Total
      expect(screen.getByText(/512 accepted/i)).toBeInTheDocument(); // Matches
      expect(screen.getByText(/28 sub-threshold/i)).toBeInTheDocument(); // No-matches
      expect(screen.getByText("94.8%")).toBeInTheDocument(); // Match Rate
      expect(screen.getByText("125 ms")).toBeInTheDocument(); // Avg Latency
    });
  });

  it("changes time window on button click and fetches updated analytics", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("540")).toBeInTheDocument();
    });

    const btn30d = screen.getByRole("button", { name: /30/i });
    fireEvent.click(btn30d);

    await waitFor(() => {
      expect(adminService.getAnalytics).toHaveBeenCalledWith(30);
    });
  });

  it("displays active threshold calibration reference info", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("v1.0.0-baseline")).toBeInTheDocument();
      expect(screen.getByText("0.405898")).toBeInTheDocument();
      expect(screen.getByText("Active Decision Threshold Benchmark")).toBeInTheDocument();
    });
  });
});
