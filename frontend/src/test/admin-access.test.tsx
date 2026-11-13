import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { RouteGuard } from "@/components/layout/RouteGuard";
import { useAuthStore } from "@/store/useAuthStore";

const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: mockReplace,
    push: vi.fn(),
  }),
  usePathname: () => "/admin/dashboard",
}));

describe("Phase 8D - Admin Access & Authorization Guards", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().clearAuth();
  });

  it("blocks unauthenticated access to admin routes and redirects to /login", () => {
    useAuthStore.setState({ isLoading: false, isAuthenticated: false, user: null });

    render(
      <RouteGuard requireAdmin={true}>
        <div>Secret Admin Dashboard</div>
      </RouteGuard>
    );

    expect(mockReplace).toHaveBeenCalledWith("/login?redirect=%2Fadmin%2Fdashboard");
    expect(screen.queryByText("Secret Admin Dashboard")).not.toBeInTheDocument();
  });

  it("blocks standard USER role from accessing admin route and redirects to /dashboard", () => {
    useAuthStore.setState({
      isLoading: false,
      isAuthenticated: true,
      user: {
        id: "usr-normal",
        email: "normal@sentinel.io",
        full_name: "Normal Operator",
        is_active: true,
        is_verified: true,
        roles: ["USER"],
        created_at: "2026-11-10T00:00:00Z",
      },
    });

    render(
      <RouteGuard requireAdmin={true}>
        <div>Secret Admin Dashboard</div>
      </RouteGuard>
    );

    expect(mockReplace).toHaveBeenCalledWith("/dashboard");
    expect(screen.queryByText("Secret Admin Dashboard")).not.toBeInTheDocument();
  });

  it("permits users with ADMIN role to access admin route", () => {
    useAuthStore.setState({
      isLoading: false,
      isAuthenticated: true,
      user: {
        id: "usr-admin",
        email: "admin@sentinel.io",
        full_name: "Platform Administrator",
        is_active: true,
        is_verified: true,
        roles: ["ADMIN"],
        created_at: "2026-11-10T00:00:00Z",
      },
    });

    render(
      <RouteGuard requireAdmin={true}>
        <div>Secret Admin Dashboard</div>
      </RouteGuard>
    );

    expect(mockReplace).not.toHaveBeenCalled();
    expect(screen.getByText("Secret Admin Dashboard")).toBeInTheDocument();
  });

  it("permits users with SUPER_ADMIN role to access admin route", () => {
    useAuthStore.setState({
      isLoading: false,
      isAuthenticated: true,
      user: {
        id: "usr-super",
        email: "root@sentinel.io",
        full_name: "Super Administrator",
        is_active: true,
        is_verified: true,
        roles: ["SUPER_ADMIN"],
        created_at: "2026-11-10T00:00:00Z",
      },
    });

    render(
      <RouteGuard requireAdmin={true}>
        <div>Secret Admin Dashboard</div>
      </RouteGuard>
    );

    expect(mockReplace).not.toHaveBeenCalled();
    expect(screen.getByText("Secret Admin Dashboard")).toBeInTheDocument();
  });
});

