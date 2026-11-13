import React from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Sidebar } from "@/components/layout/Sidebar";
import { useAuthStore } from "@/store/useAuthStore";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn() }),
}));

describe("Sidebar Navigation", () => {
  it("renders user portal routes for standard users", () => {
    useAuthStore.setState({
      user: {
        id: "user-1",
        email: "claimant@sentinelvoice.io",
        full_name: "Sarah Connor",
        is_active: true,
        is_verified: true,
        roles: ["USER"],
        created_at: "2026-11-10T00:00:00Z",
      },
      isAuthenticated: true,
    });

    render(<Sidebar isAdmin={false} />);

    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Voice Enrollment")).toBeInTheDocument();
    expect(screen.getByText("Voice Verification")).toBeInTheDocument();
    expect(screen.getByText("My Voice Profile")).toBeInTheDocument();
    expect(screen.getByText("Verification History")).toBeInTheDocument();
  });

  it("renders admin console routes when isAdmin is true", () => {
    useAuthStore.setState({
      user: {
        id: "admin-1",
        email: "admin@sentinelvoice.io",
        full_name: "System Administrator",
        is_active: true,
        is_verified: true,
        roles: ["ADMIN"],
        created_at: "2026-11-10T00:00:00Z",
      },
      isAuthenticated: true,
    });

    render(<Sidebar isAdmin={true} />);

    expect(screen.getByText("Admin Overview")).toBeInTheDocument();
    expect(screen.getByText("User Management")).toBeInTheDocument();
    expect(screen.getByText("Verification Analytics")).toBeInTheDocument();
    expect(screen.getByText("Threshold Config")).toBeInTheDocument();
    expect(screen.getByText("Audit Logs")).toBeInTheDocument();
    expect(screen.getByText("System Health")).toBeInTheDocument();
  });
});

