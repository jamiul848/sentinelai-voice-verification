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
  usePathname: () => "/admin/thresholds",
}));

describe("RouteGuard Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().clearAuth();
  });

  it("shows loading screen while auth state is resolving", () => {
    useAuthStore.setState({ isLoading: true, isAuthenticated: false, user: null });

    render(
      <RouteGuard>
        <div>Protected Content</div>
      </RouteGuard>
    );

    expect(screen.getByText(/Authenticating Sentinel Session/i)).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("redirects unauthenticated users to /login with encoded redirect param", () => {
    useAuthStore.setState({ isLoading: false, isAuthenticated: false, user: null });

    render(
      <RouteGuard>
        <div>Protected Content</div>
      </RouteGuard>
    );

    expect(mockReplace).toHaveBeenCalledWith("/login?redirect=%2Fadmin%2Fthresholds");
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("renders protected content when user is authenticated for standard route", () => {
    useAuthStore.setState({
      isLoading: false,
      isAuthenticated: true,
      user: {
        id: "u-1",
        email: "user@sentinelvoice.io",
        full_name: "Standard Operator",
        is_active: true,
        is_verified: true,
        roles: ["USER"],
        created_at: "2026-11-10T00:00:00Z",
      },
    });

    render(
      <RouteGuard requireAdmin={false}>
        <div>Standard User Protected Area</div>
      </RouteGuard>
    );

    expect(screen.getByText("Standard User Protected Area")).toBeInTheDocument();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("redirects non-admin user to /dashboard when accessing admin route", () => {
    useAuthStore.setState({
      isLoading: false,
      isAuthenticated: true,
      user: {
        id: "u-1",
        email: "user@sentinelvoice.io",
        full_name: "Standard Operator",
        is_active: true,
        is_verified: true,
        roles: ["USER"],
        created_at: "2026-11-10T00:00:00Z",
      },
    });

    render(
      <RouteGuard requireAdmin={true}>
        <div>Admin Console Protected Area</div>
      </RouteGuard>
    );

    expect(mockReplace).toHaveBeenCalledWith("/dashboard");
    expect(screen.queryByText("Admin Console Protected Area")).not.toBeInTheDocument();
  });

  it("permits administrator user to render admin route", () => {
    useAuthStore.setState({
      isLoading: false,
      isAuthenticated: true,
      user: {
        id: "u-admin",
        email: "admin@sentinelvoice.io",
        full_name: "Fleet Administrator",
        is_active: true,
        is_verified: true,
        roles: ["USER", "ADMIN"],
        created_at: "2026-11-10T00:00:00Z",
      },
    });

    render(
      <RouteGuard requireAdmin={true}>
        <div>Admin Console Protected Area</div>
      </RouteGuard>
    );

    expect(screen.getByText("Admin Console Protected Area")).toBeInTheDocument();
    expect(mockReplace).not.toHaveBeenCalled();
  });
});

