"use client";

import React, { useEffect, useState } from "react";
import { userService } from "@/lib/api/services/user.service";
import { useDemoStore } from "@/store/useDemoStore";
import { DEMO_ADMIN_USERS } from "@/config/demo";
import { AdminUserListItem } from "@/types";
import { formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Search,
  Sparkles,
} from "lucide-react";

export default function AdminUsersPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  const [users, setUsers] = useState<AdminUserListItem[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [_isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Status toggle confirmation
  const [targetUser, setTargetUser] = useState<AdminUserListItem | null>(null);
  const [isStatusDialogOpen, setIsStatusDialogOpen] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  useEffect(() => {
    async function loadUsers() {
      setIsLoading(true);
      setErrorMsg(null);

      if (isDemoMode) {
        setUsers(DEMO_ADMIN_USERS);
        setIsLoading(false);
        return;
      }

      try {
        const data = await userService.getUsers({ limit: 100 });
        setUsers(data);
      } catch (err: any) {
        setErrorMsg(err.message || "Failed to load user accounts.");
      } finally {
        setIsLoading(false);
      }
    }

    loadUsers();
  }, [isDemoMode]);

  const handleToggleStatusConfirm = async () => {
    if (!targetUser) return;
    setIsUpdatingStatus(true);
    setErrorMsg(null);

    const newStatus = !targetUser.is_active;

    try {
      if (isDemoMode) {
        setTimeout(() => {
          setUsers((prev) =>
            prev.map((u) => (u.id === targetUser.id ? { ...u, is_active: newStatus } : u))
          );
          setSuccessMsg(`User status updated to ${newStatus ? "Active" : "Suspended"} (Demo).`);
          setIsStatusDialogOpen(false);
          setIsUpdatingStatus(false);
        }, 600);
        return;
      }

      await userService.updateUserStatus(targetUser.id, newStatus);
      setUsers((prev) =>
        prev.map((u) => (u.id === targetUser.id ? { ...u, is_active: newStatus } : u))
      );
      setSuccessMsg(`User ${targetUser.email} status updated to ${newStatus ? "Active" : "Suspended"}.`);
      setIsStatusDialogOpen(false);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to modify user status.");
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const filteredUsers = users.filter((u) => {
    const q = searchTerm.toLowerCase();
    return (
      u.email.toLowerCase().includes(q) ||
      u.full_name.toLowerCase().includes(q) ||
      u.roles.some((r) => r.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-white tracking-tight">User Management & RBAC</h1>
          {isDemoMode && (
            <Badge variant="warning" className="gap-1 text-[10px]">
              <Sparkles className="w-3 h-3" /> DEMO
            </Badge>
          )}
        </div>
        <p className="text-xs sm:text-sm text-slate-400">
          Manage system identities, account operational states, and role-based permissions.
        </p>
      </div>

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Search and Quick Filters */}
      <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900 border border-slate-800">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <Input
            placeholder="Search by name, email, or role..."
            className="pl-9 text-xs h-9"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="text-xs text-slate-400">
          Total Users: <strong className="text-white">{filteredUsers.length}</strong>
        </div>
      </div>

      {/* Users Table */}
      <Card className="border-slate-800 bg-slate-900/80">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User Identity</TableHead>
                <TableHead>Roles</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Voiceprint</TableHead>
                <TableHead>Registered</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredUsers.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>
                    <div className="space-y-0.5">
                      <p className="font-semibold text-white text-xs">{item.full_name}</p>
                      <p className="text-[11px] text-slate-400 font-mono">{item.email}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {item.roles.map((role) => (
                        <Badge
                          key={role}
                          variant={
                            role === "SUPER_ADMIN"
                              ? "destructive"
                              : role === "ADMIN"
                              ? "default"
                              : "secondary"
                          }
                          className="text-[10px]"
                        >
                          {role}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>
                    {item.is_active ? (
                      <Badge variant="success" className="text-[10px] gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Active
                      </Badge>
                    ) : (
                      <Badge variant="destructive" className="text-[10px] gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-400" /> Suspended
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    {item.has_voice_profile ? (
                      <span className="text-[11px] text-emerald-400 font-medium flex items-center gap-1">
                        <Check className="w-3.5 h-3.5" /> Enrolled
                      </span>
                    ) : (
                      <span className="text-[11px] text-slate-500">None</span>
                    )}
                  </TableCell>
                  <TableCell className="text-xs text-slate-400">
                    {formatDateTime(item.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant={item.is_active ? "outline" : "success"}
                      className="text-xs h-7 px-2.5"
                      onClick={() => {
                        setTargetUser(item);
                        setIsStatusDialogOpen(true);
                      }}
                    >
                      {item.is_active ? "Suspend" : "Activate"}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Confirmation Modal */}
      <Dialog open={isStatusDialogOpen} onOpenChange={setIsStatusDialogOpen}>
        <DialogHeader>
          <DialogTitle>Confirm Account Status Modification</DialogTitle>
          <DialogDescription>
            Are you sure you want to {targetUser?.is_active ? "suspend" : "activate"} user{" "}
            <strong className="text-white">{targetUser?.email}</strong>?
          </DialogDescription>
        </DialogHeader>

        <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-400">
          Suspended users cannot authenticate, generate tokens, or execute speaker verifications.
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => setIsStatusDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            size="sm"
            variant={targetUser?.is_active ? "destructive" : "success"}
            onClick={handleToggleStatusConfirm}
            isLoading={isUpdatingStatus}
          >
            Confirm Status Change
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}
