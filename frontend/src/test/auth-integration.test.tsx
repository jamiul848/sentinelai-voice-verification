import { beforeEach, describe, expect, it, vi } from "vitest";
import { authService } from "@/lib/api/services/auth.service";
import { userService } from "@/lib/api/services/user.service";
import { consentService } from "@/lib/api/services/consent.service";
import { apiClient } from "@/lib/api/client";
import { useAuthStore } from "@/store/useAuthStore";

// Mock apiClient to test service layer contract mappings
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    defaults: { headers: {} },
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));

describe("Phase 8B - Auth & User Services Integration Contracts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().clearAuth();
  });

  it("authService.register submits to POST /api/v1/auth/register and unwraps envelope", async () => {
    const mockUser = {
      id: "u-123",
      email: "test@sentinelvoice.io",
      full_name: "Test Operator",
      is_active: true,
      is_verified: false,
      roles: ["USER" as const],
      created_at: "2026-11-13T10:00:00Z",
    };

    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        success: true,
        message: "User registered successfully.",
        data: mockUser,
      },
    });

    const result = await authService.register({
      full_name: "Test Operator",
      email: "test@sentinelvoice.io",
      password: "Password123!",
      password_confirm: "Password123!",
      accept_privacy_terms: true,
    });

    expect(apiClient.post).toHaveBeenCalledWith("/api/v1/auth/register", {
      full_name: "Test Operator",
      email: "test@sentinelvoice.io",
      password: "Password123!",
      password_confirm: "Password123!",
      accept_privacy_terms: true,
    });
    expect(result.user.email).toBe("test@sentinelvoice.io");
    expect(result.message).toBe("User registered successfully.");
  });

  it("authService.login submits to POST /api/v1/auth/login and unwraps TokenResponse", async () => {
    const mockTokenResponse = {
      access_token: "jwt-access-token-xyz",
      refresh_token: "opaque-refresh-token-abc",
      token_type: "bearer",
      expires_in: 900,
      user: {
        id: "u-456",
        email: "sarah@sentinelvoice.io",
        full_name: "Sarah Connor",
        is_active: true,
        is_verified: true,
        roles: ["USER" as const],
        created_at: "2026-11-13T10:00:00Z",
      },
    };

    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        success: true,
        message: "Login successful.",
        data: mockTokenResponse,
      },
    });

    const data = await authService.login({
      email: "sarah@sentinelvoice.io",
      password: "ArgonPassword!123",
    });

    expect(apiClient.post).toHaveBeenCalledWith("/api/v1/auth/login", {
      email: "sarah@sentinelvoice.io",
      password: "ArgonPassword!123",
    });
    expect(data.access_token).toBe("jwt-access-token-xyz");
    expect(data.user.email).toBe("sarah@sentinelvoice.io");
  });

  it("userService calls PATCH /api/v1/users/me for display name update", async () => {
    const updatedUser = {
      id: "u-123",
      email: "sarah@sentinelvoice.io",
      full_name: "Dr. Sarah Connor",
      is_active: true,
      is_verified: true,
      roles: ["USER" as const],
      created_at: "2026-11-13T10:00:00Z",
    };

    (apiClient.patch as any).mockResolvedValueOnce({
      data: {
        success: true,
        message: "Profile updated successfully.",
        data: updatedUser,
      },
    });

    const res = await userService.updateProfile({ full_name: "Dr. Sarah Connor" });

    expect(apiClient.patch).toHaveBeenCalledWith("/api/v1/users/me", {
      full_name: "Dr. Sarah Connor",
    });
    expect(res.full_name).toBe("Dr. Sarah Connor");
  });

  it("userService calls POST /api/v1/users/change-password with current and new password confirmation", async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        success: true,
        message: "Password updated successfully. Existing sessions have been terminated.",
        data: { password_changed: true },
      },
    });

    const res = await userService.changePassword({
      current_password: "OldPassword!123",
      new_password: "NewPassword!456",
      new_password_confirm: "NewPassword!456",
    });

    expect(apiClient.post).toHaveBeenCalledWith("/api/v1/users/change-password", {
      current_password: "OldPassword!123",
      new_password: "NewPassword!456",
      new_password_confirm: "NewPassword!456",
    });
    expect(res.message).toContain("Password updated successfully");
  });

  it("consentService calls POST /api/v1/consent/revoke for biometric shredding", async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        success: true,
        message: "Biometric processing consent revoked.",
        data: { revoked: true },
      },
    });

    const res = await consentService.revoke("User voluntary revocation");

    expect(apiClient.post).toHaveBeenCalledWith("/api/v1/consent/revoke", {
      consent_type: "VOICE_BIOMETRIC_ENROLLMENT",
      reason: "User voluntary revocation",
    });
    expect(res.message).toBe("Biometric processing consent revoked.");
  });

  it("userService admin operations map to /api/v1/admin/users endpoints", async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: { success: true, message: "OK", data: [] },
    });
    await userService.getUsers({ skip: 0, limit: 50 });
    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/admin/users", {
      params: { skip: 0, limit: 50 },
    });

    (apiClient.patch as any).mockResolvedValueOnce({
      data: { success: true, message: "OK", data: {} },
    });
    await userService.updateUserStatus("u-999", false);
    expect(apiClient.patch).toHaveBeenCalledWith("/api/v1/admin/users/u-999/status", {
      is_active: false,
    });
  });
});

