import { apiClient } from "../client";
import { AdminUserListItem, ChangePasswordPayload, UpdateProfilePayload, User } from "@/types";

export const userService = {
  /**
   * Fetch currently authenticated user identity.
   */
  async getMe(): Promise<User> {
    const res = await apiClient.get("/api/v1/users/me");
    return res.data.data || res.data;
  },

  /**
   * Update profile information (e.g. display name).
   * Maps to FastAPI PATCH /api/v1/users/me.
   */
  async updateProfile(payload: UpdateProfilePayload): Promise<User> {
    const res = await apiClient.patch("/api/v1/users/me", payload);
    return res.data.data || res.data;
  },

  /**
   * Change user password.
   * Maps to FastAPI POST /api/v1/users/change-password.
   */
  async changePassword(payload: ChangePasswordPayload): Promise<{ message: string }> {
    const res = await apiClient.post("/api/v1/users/change-password", payload);
    return {
      message: res.data.message || "Password updated successfully.",
    };
  },

  /**
   * Administrator: List system users.
   * Maps to FastAPI GET /api/v1/admin/users.
   */
  async getUsers(params?: { skip?: number; limit?: number; active_only?: boolean }): Promise<AdminUserListItem[]> {
    const res = await apiClient.get("/api/v1/admin/users", { params });
    return res.data.data || res.data;
  },

  /**
   * Administrator: Update user active status (activate/suspend).
   * Maps to FastAPI PATCH /api/v1/admin/users/{userId}/status.
   */
  async updateUserStatus(userId: string, isActive: boolean): Promise<User> {
    const res = await apiClient.patch(`/api/v1/admin/users/${userId}/status`, { is_active: isActive });
    return res.data.data || res.data;
  },

  /**
   * Administrator: Update user RBAC roles.
   * Maps to FastAPI PATCH /api/v1/admin/users/{userId}/roles.
   */
  async updateUserRoles(userId: string, roles: string[]): Promise<User> {
    const res = await apiClient.patch(`/api/v1/admin/users/${userId}/roles`, { roles });
    return res.data.data || res.data;
  },

  /**
   * Administrator: Fetch single user by UUID.
   * Maps to FastAPI GET /api/v1/admin/users/{userId}.
   */
  async getUserById(userId: string): Promise<User> {
    const res = await apiClient.get(`/api/v1/admin/users/${userId}`);
    return res.data.data || res.data;
  },

  /**
   * Administrator: Delete a user account.
   * Maps to FastAPI DELETE /api/v1/admin/users/{userId}.
   */
  async deleteUser(userId: string): Promise<{ deleted: boolean }> {
    const res = await apiClient.delete(`/api/v1/admin/users/${userId}`);
    return res.data.data || res.data;
  },
};
