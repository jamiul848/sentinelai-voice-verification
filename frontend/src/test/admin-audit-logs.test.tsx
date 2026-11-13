import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import AdminAuditLogsPage from "@/app/admin/audit-logs/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { adminService } from "@/lib/api/services/admin.service";
import { useDemoStore } from "@/store/useDemoStore";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/admin/audit-logs",
}));

vi.mock("@/lib/api/services/admin.service", () => ({
  adminService: {
    getAuditLogs: vi.fn(),
  },
}));

describe("Phase 8D - Admin Immutable Audit Logs Page", () => {
  let queryClient: QueryClient;

  const mockLogsResponse = {
    items: [
      {
        id: "audit-001",
        action: "USER_STATUS_UPDATED",
        resource_type: "user",
        resource_id: "usr-456",
        actor_user_id: "adm-123",
        actor_email: "secops@sentinel.io",
        payload: { is_active: false },
        created_at: "2026-11-13T10:15:00Z",
      },
      {
        id: "audit-002",
        action: "THRESHOLD_ACTIVATED",
        resource_type: "threshold_configuration",
        resource_id: "th-789",
        actor_user_id: "adm-123",
        actor_email: "secops@sentinel.io",
        payload: { version_tag: "v2.0.0" },
        created_at: "2026-11-13T11:20:00Z",
      },
    ],
    total: 2,
    limit: 100,
    offset: 0,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    useDemoStore.setState({ isDemoMode: false });
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    (adminService.getAuditLogs as any).mockResolvedValue(mockLogsResponse);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AdminAuditLogsPage />
      </QueryClientProvider>
    );

  it("renders audit ledger records from backend", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("USER_STATUS_UPDATED")).toBeInTheDocument();
      expect(screen.getByText("THRESHOLD_ACTIVATED")).toBeInTheDocument();
      expect(screen.getByText("usr-456")).toBeInTheDocument();
      expect(screen.getByText("th-789")).toBeInTheDocument();
    });
  });

  it("filters audit events by category button", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("USER_STATUS_UPDATED")).toBeInTheDocument();
      expect(screen.getByText("THRESHOLD_ACTIVATED")).toBeInTheDocument();
    });

    const userCatBtn = screen.getByRole("button", { name: "User" });
    fireEvent.click(userCatBtn);

    expect(screen.getByText("USER_STATUS_UPDATED")).toBeInTheDocument();
    expect(screen.queryByText("THRESHOLD_ACTIVATED")).not.toBeInTheDocument();
  });

  it("opens inspector modal when clicking Inspect", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("USER_STATUS_UPDATED")).toBeInTheDocument();
    });

    const inspectButtons = screen.getAllByRole("button", { name: /Inspect/i });
    fireEvent.click(inspectButtons[0]);

    expect(screen.getByRole("heading", { name: /Audit Log Record Inspector/i })).toBeInTheDocument();
    expect(screen.getByText(/Sanitized immutable change event/i)).toBeInTheDocument();
  });
});
