import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import AdminUsersPage from "@/app/admin/users/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { userService } from "@/lib/api/services/user.service";
import { useAuthStore } from "@/store/useAuthStore";
import { useDemoStore } from "@/store/useDemoStore";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/admin/users",
}));

vi.mock("@/lib/api/services/user.service", () => ({
  userService: {
    getUsers: vi.fn(),
    getUserById: vi.fn(),
    updateUserStatus: vi.fn(),
    updateUserRoles: vi.fn(),
    deleteUser: vi.fn(),
  },
}));

describe("Phase 8D - Admin Users Management Page", () => {
  let queryClient: QueryClient;

  const mockUsersList = [
    {
      id: "usr-1",
      email: "operator1@sentinel.io",
      full_name: "Operator One",
      is_active: true,
      is_verified: true,
      roles: ["USER"],
      created_at: "2026-11-10T10:00:00Z",
    },
    {
      id: "usr-2",
      email: "admin2@sentinel.io",
      full_name: "Admin Two",
      is_active: true,
      is_verified: true,
      roles: ["ADMIN"],
      created_at: "2026-11-11T11:00:00Z",
    },
    {
      id: "usr-3",
      email: "suspended@sentinel.io",
      full_name: "Suspended Account",
      is_active: false,
      is_verified: true,
      roles: ["USER"],
      created_at: "2026-11-12T12:00:00Z",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    useDemoStore.setState({ isDemoMode: false });
    useAuthStore.setState({
      isLoading: false,
      isAuthenticated: true,
      user: {
        id: "usr-admin-current",
        email: "super@sentinel.io",
        full_name: "Super Admin",
        is_active: true,
        is_verified: true,
        roles: ["SUPER_ADMIN"],
        created_at: "2026-11-01T00:00:00Z",
      },
    });

    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    (userService.getUsers as any).mockResolvedValue(mockUsersList);
    (userService.updateUserStatus as any).mockResolvedValue({
      id: "usr-1",
      is_active: false,
    });
    (userService.updateUserRoles as any).mockResolvedValue({
      id: "usr-1",
      roles: ["USER", "ADMIN"],
    });
    (userService.deleteUser as any).mockResolvedValue({
      message: "User deleted",
    });
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AdminUsersPage />
      </QueryClientProvider>
    );

  it("renders user roster loaded from backend", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("operator1@sentinel.io")).toBeInTheDocument();
      expect(screen.getByText("admin2@sentinel.io")).toBeInTheDocument();
      expect(screen.getByText("suspended@sentinel.io")).toBeInTheDocument();
    });
  });

  it("filters users dynamically based on search query", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("operator1@sentinel.io")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search by name, email, or UUID/i);
    fireEvent.change(searchInput, { target: { value: "suspended" } });

    expect(screen.getByText("suspended@sentinel.io")).toBeInTheDocument();
    expect(screen.queryByText("operator1@sentinel.io")).not.toBeInTheDocument();
  });

  it("opens status dialog and submits account deactivation", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("operator1@sentinel.io")).toBeInTheDocument();
    });

    // Find Deactivate button for usr-1
    const deactivateBtn = screen.getByTestId("status-btn-usr-1");
    fireEvent.click(deactivateBtn);

    expect(screen.getByText(/Confirm Status Mutation/i)).toBeInTheDocument();

    const confirmBtn = screen.getByRole("button", { name: /Deactivate Account/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(userService.updateUserStatus).toHaveBeenCalledWith("usr-1", false);
    });
  });

  it("opens role management dialog and submits role assignment", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("operator1@sentinel.io")).toBeInTheDocument();
    });

    const roleBtn = screen.getByTestId("role-btn-usr-1");
    fireEvent.click(roleBtn);

    expect(screen.getByRole("heading", { name: /RBAC Role Assignment/i })).toBeInTheDocument();

    // Toggle ADMIN role
    const adminRoleOption = screen.getByTestId("role-option-ADMIN");
    fireEvent.click(adminRoleOption);

    const saveRolesBtn = screen.getByRole("button", { name: /Save Roles/i });
    fireEvent.click(saveRolesBtn);

    await waitFor(() => {
      expect(userService.updateUserRoles).toHaveBeenCalled();
    });
  });

  it("opens delete confirmation dialog and deletes disposable user", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("operator1@sentinel.io")).toBeInTheDocument();
    });

    const deleteBtn = screen.getByTestId("delete-btn-usr-1");
    fireEvent.click(deleteBtn);

    expect(screen.getByText(/Confirm Account Deletion/i)).toBeInTheDocument();

    const confirmDeleteBtn = screen.getByRole("button", { name: /Permanently Delete/i });
    fireEvent.click(confirmDeleteBtn);

    await waitFor(() => {
      expect(userService.deleteUser).toHaveBeenCalledWith("usr-1");
    });
  });
});
