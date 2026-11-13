"use client";

import React, { useState } from "react";
import { useAuthStore } from "@/store/useAuthStore";
import { useDemoStore } from "@/store/useDemoStore";
import {
  useAdminUsers,
  useDeleteUser,
  useUpdateUserRoles,
  useUpdateUserStatus,
} from "@/hooks/useAdmin";
import { AdminUserListItem } from "@/types";
import { formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertCircle,
  CheckCircle2,
  Lock,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  Sparkles,
  Trash2,
  UserCheck,
  UserX,
} from "lucide-react";

export default function AdminUsersPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);
  const currentUser = useAuthStore((s) => s.user);

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "ACTIVE" | "INACTIVE">("ALL");
  const [roleFilter, setRoleFilter] = useState<"ALL" | "ADMIN" | "USER">("ALL");

  const { data: users = [], isLoading, error, refetch, isFetching } = useAdminUsers({ limit: 100 });
  const updateStatusMutation = useUpdateUserStatus();
  const updateRolesMutation = useUpdateUserRoles();
  const deleteUserMutation = useDeleteUser();

  // Status toggle confirmation
  const [targetUser, setTargetUser] = useState<AdminUserListItem | null>(null);
  const [isStatusDialogOpen, setIsStatusDialogOpen] = useState(false);

  // Role modification dialog
  const [roleUser, setRoleUser] = useState<AdminUserListItem | null>(null);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [isRoleDialogOpen, setIsRoleDialogOpen] = useState(false);

  // User details dialog
  const [detailUser, setDetailUser] = useState<AdminUserListItem | null>(null);
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false);

  // Delete confirmation dialog
  const [deleteTarget, setDeleteTarget] = useState<AdminUserListItem | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Filtered users
  const filteredUsers = users.filter((u) => {
    const term = searchTerm.toLowerCase();
    const matchesSearch =
      u.full_name?.toLowerCase().includes(term) ||
      u.email.toLowerCase().includes(term) ||
      u.id.toLowerCase().includes(term);

    const matchesStatus =
      statusFilter === "ALL" ||
      (statusFilter === "ACTIVE" && u.is_active) ||
      (statusFilter === "INACTIVE" && !u.is_active);

    const matchesRole =
      roleFilter === "ALL" ||
      u.roles?.some((r) => r.toUpperCase() === roleFilter);

    return matchesSearch && matchesStatus && matchesRole;
  });

  const handleOpenStatusDialog = (user: AdminUserListItem) => {
    setActionError(null);
    setActionSuccess(null);
    setTargetUser(user);
    setIsStatusDialogOpen(true);
  };

  const handleConfirmStatusToggle = async () => {
    if (!targetUser) return;
    setActionError(null);
    try {
      await updateStatusMutation.mutateAsync({
        userId: targetUser.id,
        isActive: !targetUser.is_active,
      });
      setActionSuccess(`User ${targetUser.email} ${!targetUser.is_active ? "activated" : "deactivated"} successfully.`);
      setIsStatusDialogOpen(false);
    } catch (err: any) {
      setActionError(err.response?.data?.message || err.message || "Failed to update user status.");
    }
  };

  const handleOpenRoleDialog = (user: AdminUserListItem) => {
    setActionError(null);
    setActionSuccess(null);
    setRoleUser(user);
    setSelectedRoles(user.roles ? [...user.roles] : ["USER"]);
    setIsRoleDialogOpen(true);
  };

  const handleToggleRoleSelection = (role: string) => {
    setSelectedRoles((prev) =>
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role]
    );
  };

  const handleConfirmRoleUpdate = async () => {
    if (!roleUser) return;
    if (selectedRoles.length === 0) {
      setActionError("A user must have at least one assigned role.");
      return;
    }
    setActionError(null);
    try {
      await updateRolesMutation.mutateAsync({
        userId: roleUser.id,
        roles: selectedRoles,
      });
      setActionSuccess(`Roles updated for ${roleUser.email}.`);
      setIsRoleDialogOpen(false);
    } catch (err: any) {
      setActionError(err.response?.data?.message || err.message || "Failed to update roles.");
    }
  };

  const handleOpenDeleteDialog = (user: AdminUserListItem) => {
    setActionError(null);
    setActionSuccess(null);
    setDeleteTarget(user);
    setIsDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setActionError(null);
    try {
      await deleteUserMutation.mutateAsync(deleteTarget.id);
      setActionSuccess(`User account ${deleteTarget.email} permanently removed.`);
      setIsDeleteDialogOpen(false);
    } catch (err: any) {
      setActionError(err.response?.data?.message || err.message || "Failed to delete account.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Identity & User Management</h1>
            {isDemoMode && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <Sparkles className="w-3 h-3" /> DEMO
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Control platform accounts, enforce RBAC role assignments, and oversee account activation lifecycles.
          </p>
        </div>

        <Button
          size="sm"
          variant="outline"
          onClick={() => refetch()}
          disabled={isFetching}
          className="gap-1.5 text-xs border-slate-700 bg-slate-900/60"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${isFetching ? "animate-spin" : ""}`} />
          <span>Refresh Fleet</span>
        </Button>
      </div>

      {/* Notifications */}
      {actionSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-xs text-emerald-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{actionSuccess}</span>
          </div>
          <Button size="sm" variant="ghost" onClick={() => setActionSuccess(null)} className="h-6 text-xs text-slate-400">
            Dismiss
          </Button>
        </div>
      )}

      {actionError && (
        <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-800/60 text-xs text-red-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400" />
            <span>{actionError}</span>
          </div>
          <Button size="sm" variant="ghost" onClick={() => setActionError(null)} className="h-6 text-xs text-slate-400">
            Dismiss
          </Button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <Input
            placeholder="Search by name, email, or UUID..."
            className="pl-9 text-xs h-9 bg-slate-950/80 border-slate-700"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Status filter */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setStatusFilter("ALL")}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                statusFilter === "ALL" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              All Status
            </button>
            <button
              onClick={() => setStatusFilter("ACTIVE")}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                statusFilter === "ACTIVE" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Active
            </button>
            <button
              onClick={() => setStatusFilter("INACTIVE")}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                statusFilter === "INACTIVE" ? "bg-amber-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Suspended
            </button>
          </div>

          {/* Role filter */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setRoleFilter("ALL")}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                roleFilter === "ALL" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              All Roles
            </button>
            <button
              onClick={() => setRoleFilter("ADMIN")}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                roleFilter === "ADMIN" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Admins
            </button>
            <button
              onClick={() => setRoleFilter("USER")}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                roleFilter === "USER" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Users
            </button>
          </div>
        </div>
      </div>

      {/* User Table */}
      <Card className="border-slate-800 bg-slate-900/80">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User / Identity</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Verified</TableHead>
                <TableHead>Assigned Roles</TableHead>
                <TableHead>Enrolled At</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-10 text-xs text-slate-500">
                    Loading platform user records...
                  </TableCell>
                </TableRow>
              ) : filteredUsers.length > 0 ? (
                filteredUsers.map((u) => {
                  const isCurrent = currentUser?.id === u.id;
                  const isAdmin = u.roles?.some((r) => r === "ADMIN" || r === "SUPER_ADMIN");

                  return (
                    <TableRow key={u.id} className="hover:bg-slate-800/40">
                      <TableCell>
                        <div className="space-y-0.5">
                          <button
                            onClick={() => {
                              setDetailUser(u);
                              setIsDetailDialogOpen(true);
                            }}
                            className="font-semibold text-white hover:text-blue-400 text-left text-xs transition-colors"
                          >
                            {u.full_name || "Unnamed Officer"}
                          </button>
                          <div className="text-[11px] text-slate-400 font-mono flex items-center gap-1.5">
                            <span>{u.email}</span>
                            {isCurrent && (
                              <Badge variant="outline" className="text-[9px] px-1 py-0 border-blue-500/40 text-blue-400">
                                YOU
                              </Badge>
                            )}
                          </div>
                        </div>
                      </TableCell>

                      <TableCell>
                        {u.is_active ? (
                          <Badge variant="success" className="text-[10px]">
                            ACTIVE
                          </Badge>
                        ) : (
                          <Badge variant="destructive" className="text-[10px]">
                            SUSPENDED
                          </Badge>
                        )}
                      </TableCell>

                      <TableCell>
                        {u.is_verified ? (
                          <span className="text-emerald-400 text-xs flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Verified
                          </span>
                        ) : (
                          <span className="text-slate-500 text-xs">Unverified</span>
                        )}
                      </TableCell>

                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {u.roles?.map((r) => (
                            <Badge
                              key={r}
                              variant={r === "ADMIN" || r === "SUPER_ADMIN" ? "cyber" : "secondary"}
                              className="text-[10px]"
                            >
                              {r}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>

                      <TableCell className="text-xs text-slate-400 font-mono">
                        {formatDateTime(u.created_at)}
                      </TableCell>

                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Inspect details */}
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              setDetailUser(u);
                              setIsDetailDialogOpen(true);
                            }}
                            className="text-xs h-7 px-2 text-slate-300 hover:text-white"
                          >
                            Inspect
                          </Button>

                          {/* Toggle Active Status */}
                          <Button
                            size="sm"
                            variant="outline"
                            data-testid={`status-btn-${u.id}`}
                            onClick={() => handleOpenStatusDialog(u)}
                            disabled={isCurrent}
                            title={isCurrent ? "Cannot modify your own account status" : undefined}
                            className={`text-xs h-7 px-2 border-slate-700 ${
                              u.is_active ? "text-amber-400 hover:text-amber-300" : "text-emerald-400 hover:text-emerald-300"
                            }`}
                          >
                            {u.is_active ? "Deactivate" : "Activate"}
                          </Button>

                          {/* Manage Roles */}
                          <Button
                            size="sm"
                            variant="secondary"
                            data-testid={`role-btn-${u.id}`}
                            onClick={() => handleOpenRoleDialog(u)}
                            className="text-xs h-7 px-2"
                          >
                            Roles
                          </Button>

                          {/* Delete Account */}
                          <Button
                            size="sm"
                            variant="ghost"
                            data-testid={`delete-btn-${u.id}`}
                            onClick={() => handleOpenDeleteDialog(u)}
                            disabled={isCurrent}
                            title={isCurrent ? "Cannot delete your own account" : undefined}
                            className="text-xs h-7 px-2 text-red-400 hover:text-red-300 hover:bg-red-950/40"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-10 text-xs text-slate-500">
                    No matching user accounts discovered.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Account Status Confirmation Dialog */}
      <Dialog open={isStatusDialogOpen} onOpenChange={setIsStatusDialogOpen}>
        <DialogContent className="max-w-md bg-slate-900 border-slate-800 text-slate-100">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-400" />
              <span>Confirm Status Mutation</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-400">
              Are you sure you want to {targetUser?.is_active ? "deactivate" : "reactivate"} the account for{" "}
              <strong className="text-white">{targetUser?.email}</strong>?
            </DialogDescription>
          </DialogHeader>

          <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 text-xs text-slate-300 space-y-1">
            <p>
              {targetUser?.is_active
                ? "Deactivating this account immediately revokes all active JWT and refresh sessions. The user will be unable to authenticate or verify voiceprints."
                : "Reactivating this account restores biometric verification and login access."}
            </p>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsStatusDialogOpen(false)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleConfirmStatusToggle}
              isLoading={updateStatusMutation.isPending}
              className={`text-xs ${
                targetUser?.is_active
                  ? "bg-amber-600 hover:bg-amber-500 text-white"
                  : "bg-emerald-600 hover:bg-emerald-500 text-white"
              }`}
            >
              {targetUser?.is_active ? "Deactivate Account" : "Activate Account"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Role Management Dialog */}
      <Dialog open={isRoleDialogOpen} onOpenChange={setIsRoleDialogOpen}>
        <DialogContent className="max-w-md bg-slate-900 border-slate-800 text-slate-100">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-purple-400" />
              <span>RBAC Role Assignment</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-400">
              Assign roles for <strong className="text-white">{roleUser?.email}</strong>.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            {["USER", "ADMIN", "SUPER_ADMIN"].map((roleName) => {
              const isChecked = selectedRoles.includes(roleName);
              return (
                <div
                  key={roleName}
                  data-testid={`role-option-${roleName}`}
                  onClick={() => handleToggleRoleSelection(roleName)}
                  className={`p-3 rounded-lg border flex items-center justify-between cursor-pointer transition-colors ${
                    isChecked
                      ? "bg-purple-950/30 border-purple-500/50 text-white"
                      : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <div className="space-y-0.5">
                    <span className="font-semibold text-xs">{roleName}</span>
                    <p className="text-[11px] text-slate-400">
                      {roleName === "ADMIN"
                        ? "Fleet oversight, user activation, audit inspection."
                        : roleName === "SUPER_ADMIN"
                        ? "Full root authorization across all platform resources."
                        : "Standard biometric voice verification and enrollment."}
                    </p>
                  </div>
                  <div
                    className={`w-4 h-4 rounded border flex items-center justify-center ${
                      isChecked ? "bg-purple-600 border-purple-500 text-white" : "border-slate-700"
                    }`}
                  >
                    {isChecked && <CheckCircle2 className="w-3.5 h-3.5" />}
                  </div>
                </div>
              );
            })}
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsRoleDialogOpen(false)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleConfirmRoleUpdate}
              isLoading={updateRolesMutation.isPending}
              className="bg-purple-600 hover:bg-purple-500 text-white text-xs"
            >
              Save Roles
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* User Details Inspector Dialog */}
      <Dialog open={isDetailDialogOpen} onOpenChange={setIsDetailDialogOpen}>
        <DialogContent className="max-w-lg bg-slate-900 border-slate-800 text-slate-100">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-blue-400" />
              <span>Identity Profile Inspector</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-400">
              Sanitized account metadata for {detailUser?.full_name || detailUser?.email}.
            </DialogDescription>
          </DialogHeader>

          {detailUser && (
            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-400">User UUID</span>
                  <p className="font-mono text-white text-[11px] truncate">{detailUser.id}</p>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-400">Email Address</span>
                  <p className="font-mono text-white text-[11px] truncate">{detailUser.email}</p>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-400">Account Status</span>
                  <p className="font-semibold text-white">
                    {detailUser.is_active ? "Active" : "Suspended"}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-400">Email Verification</span>
                  <p className="font-semibold text-white">
                    {detailUser.is_verified ? "Verified" : "Pending Verification"}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-400">Assigned Roles</span>
                  <p className="font-mono text-blue-300">
                    {detailUser.roles?.join(", ") || "None"}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-400">Registered At</span>
                  <p className="text-slate-200 text-[11px] font-mono">
                    {formatDateTime(detailUser.created_at)}
                  </p>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-blue-950/30 border border-blue-800/40 text-[11px] text-blue-300">
                <strong>Data Privacy Guarantee:</strong> Passwords, credentials, and cryptographic biometric embeddings are strictly isolated and never rendered in administrative views.
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsDetailDialogOpen(false)}
              className="text-xs"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent className="max-w-md bg-slate-900 border-slate-800 text-slate-100">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-red-400" />
              <span>Confirm Account Deletion</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-400">
              Permanently remove account <strong className="text-white">{deleteTarget?.email}</strong>.
            </DialogDescription>
          </DialogHeader>

          <div className="p-3 rounded-lg bg-red-950/40 border border-red-800/60 text-xs text-red-200 space-y-1">
            <p>
              This operation permanently deletes the user account, associated verification history, and triggers vector shredding for enrolled voiceprints. This action cannot be undone.
            </p>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsDeleteDialogOpen(false)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleConfirmDelete}
              isLoading={deleteUserMutation.isPending}
              className="bg-red-600 hover:bg-red-500 text-white text-xs"
            >
              Permanently Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
