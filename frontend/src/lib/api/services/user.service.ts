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
   * Update profile information.
   */
  async updateProfile(payload: UpdateProfilePayload): Promise<User> {
    const res = await apiClient.put("/api/v1/users/me", payload);
    return res.data.data || res.data;
  },

  /**
   * Change user password.
   */
  async changePassword(payload: ChangePasswordPayload): Promise<{ message: string }> {
    const res = await apiClient.put("/api/v1/users/me/password", payload);
    return res.data;
  },

  /**
   * Administrator: List system users.
   */
  async getUsers(params?: { skip?: number; limit?: number }): Promise<AdminUserListItem[]> {
    const res = await apiClient.get("/api/v1/users", { params });
    return res.data.data || res.data;
  },

  /**
   * Administrator: Update user active status.
   */
  async updateUserStatus(userId: string, isActive: boolean): Promise<User> {
    const res = await apiClient.put(`/api/v1/users/${userId}/status`, { is_active: isActive });
    return res.data.data || res.data;
  },

  /**
   * Administrator: Update user RBAC roles.
   */
  async updateUserRoles(userId: string, roles: string[]): Promise<User> {
    const res = await apiClient.put(`/api/v1/users/${userId}/roles`, { roles });
    return res.data.data || res.data;
  },
};

