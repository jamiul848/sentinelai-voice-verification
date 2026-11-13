import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import AdminVoiceProfilesPage from "@/app/admin/voice-profiles/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { adminService } from "@/lib/api/services/admin.service";
import { useDemoStore } from "@/store/useDemoStore";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/admin/voice-profiles",
}));

vi.mock("@/lib/api/services/admin.service", () => ({
  adminService: {
    getVoiceProfiles: vi.fn(),
    revokeVoiceProfile: vi.fn(),
  },
}));

describe("Phase 8D - Admin Voice Profiles Management", () => {
  let queryClient: QueryClient;

  const mockProfilesResponse = {
    items: [
      {
        id: "prof-001-active-uuid",
        user_id: "usr-1",
        user_email: "alice@sentinel.io",
        user_full_name: "Alice Operator",
        status: "ACTIVE",
        sample_count: 3,
        mean_pairwise_similarity: 0.884,
        model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
        created_at: "2026-11-12T10:00:00Z",
      },
      {
        id: "prof-002-revoked-uuid",
        user_id: "usr-2",
        user_email: "bob@sentinel.io",
        user_full_name: "Bob Operator",
        status: "REVOKED",
        sample_count: 3,
        mean_pairwise_similarity: 0.852,
        model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
        created_at: "2026-11-10T14:00:00Z",
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

    (adminService.getVoiceProfiles as any).mockResolvedValue(mockProfilesResponse);
    (adminService.revokeVoiceProfile as any).mockResolvedValue({
      profile_id: "prof-001-active-uuid",
      status: "REVOKED",
      message: "Biometric profile revoked and encrypted embeddings shredded.",
    });
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AdminVoiceProfilesPage />
      </QueryClientProvider>
    );

  it("renders biometric profile registry with user emails and status", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("alice@sentinel.io")).toBeInTheDocument();
      expect(screen.getByText("bob@sentinel.io")).toBeInTheDocument();
      expect(screen.getByText("Vector Shredded")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Revoke & Shred/i })).toBeInTheDocument();
    });
  });

  it("filters profiles by email search input", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("alice@sentinel.io")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search by user email, name, or profile UUID/i);
    fireEvent.change(searchInput, { target: { value: "bob" } });

    expect(screen.getByText("bob@sentinel.io")).toBeInTheDocument();
    expect(screen.queryByText("alice@sentinel.io")).not.toBeInTheDocument();
  });

  it("opens revocation dialog and invokes revokeVoiceProfile", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("alice@sentinel.io")).toBeInTheDocument();
    });

    const revokeBtn = screen.getByRole("button", { name: /Revoke & Shred/i });
    fireEvent.click(revokeBtn);

    expect(screen.getByText(/Confirm Administrative Revocation/i)).toBeInTheDocument();

    const confirmBtn = screen.getByRole("button", { name: /Confirm Revocation & Shred/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(adminService.revokeVoiceProfile).toHaveBeenCalledWith(
        "prof-001-active-uuid"
      );
    });
  });
});
