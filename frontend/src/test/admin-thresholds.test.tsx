import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import AdminThresholdsPage from "@/app/admin/thresholds/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { adminService } from "@/lib/api/services/admin.service";
import { useDemoStore } from "@/store/useDemoStore";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/admin/thresholds",
}));

vi.mock("@/lib/api/services/admin.service", () => ({
  adminService: {
    getThresholds: vi.fn(),
    createThreshold: vi.fn(),
    activateThreshold: vi.fn(),
  },
}));

describe("Phase 8D - Dynamic Threshold Governance Page", () => {
  let queryClient: QueryClient;

  const mockThresholds = [
    {
      id: "th-active-1",
      version_tag: "v1.0.0-baseline",
      threshold_value: 0.405898,
      calibration_dataset: "LibriSpeech dev-clean",
      optimization_criterion: "equal_error_rate_minimization",
      model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
      is_active: true,
      eer_reported: 0.0125,
      created_at: "2026-11-10T10:00:00Z",
    },
    {
      id: "th-candidate-2",
      version_tag: "v2.0.0-strict",
      threshold_value: 0.485,
      calibration_dataset: "VoxCeleb1 test",
      optimization_criterion: "fnr_minimization",
      model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
      is_active: false,
      eer_reported: 0.0098,
      created_at: "2026-11-12T14:00:00Z",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    useDemoStore.setState({ isDemoMode: false });
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    (adminService.getThresholds as any).mockResolvedValue(mockThresholds);
    (adminService.createThreshold as any).mockResolvedValue({
      id: "th-new-3",
      version_tag: "v3.0.0-custom",
      threshold_value: 0.42,
      is_active: false,
    });
    (adminService.activateThreshold as any).mockResolvedValue({
      id: "th-candidate-2",
      version_tag: "v2.0.0-strict",
      is_active: true,
    });
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AdminThresholdsPage />
      </QueryClientProvider>
    );

  it("renders active threshold banner and threshold configurations list", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("Active Operational Decision Boundary")).toBeInTheDocument();
      expect(screen.getAllByText("v1.0.0-baseline").length).toBeGreaterThan(0);
      expect(screen.getByText("v2.0.0-strict")).toBeInTheDocument();
      expect(screen.getByText("Currently Active")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Activate/i })).toBeInTheDocument();
    });
  });

  it("opens create modal and registers a new calibrated threshold", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getAllByText("v1.0.0-baseline").length).toBeGreaterThan(0);
    });

    const registerBtn = screen.getByRole("button", { name: /Register Threshold/i });
    fireEvent.click(registerBtn);

    expect(screen.getByRole("heading", { name: /Register Calibrated Threshold/i })).toBeInTheDocument();

    const versionInput = screen.getByPlaceholderText(/e\.g\. voxceleb-eer-v2\.0/i);
    fireEvent.change(versionInput, { target: { value: "voxceleb-v3.0" } });

    const saveBtn = screen.getByRole("button", { name: /Save Threshold/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(adminService.createThreshold).toHaveBeenCalled();
    });
  });

  it("opens activate modal and confirms threshold activation", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("v2.0.0-strict")).toBeInTheDocument();
    });

    const activateBtn = screen.getByRole("button", { name: /Activate/i });
    fireEvent.click(activateBtn);

    expect(screen.getByRole("heading", { name: /Confirm Operating Boundary Activation/i })).toBeInTheDocument();

    const confirmBtn = screen.getByRole("button", { name: /Confirm Activation/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(adminService.activateThreshold).toHaveBeenCalledWith("th-candidate-2");
    });
  });
});
