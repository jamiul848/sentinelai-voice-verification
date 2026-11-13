m"use client";

import React, { useState } from "react";
import { useAuthStore } from "@/store/useAuthStore";
import { userService } from "@/lib/api/services/user.service";
import { useDemoStore } from "@/store/useDemoStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, CheckCircle2, KeyRound, User as UserIcon } from "lucide-react";

export default function SettingsPage() {
  const { user, setUser } = useAuthStore();
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  // Profile update state
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);

  // Password change state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileSuccess(null);
    setProfileSaving(true);

    try {
      if (isDemoMode) {
        setTimeout(() => {
          if (user) setUser({ ...user, full_name: fullName });
          setProfileSuccess("Demo profile name updated successfully.");
          setProfileSaving(false);
        }, 600);
        return;
      }

      const updated = await userService.updateProfile({ full_name: fullName });
      setUser(updated);
      setProfileSuccess("Profile updated successfully.");
    } catch {
      // Show error
    } finally {
      setProfileSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    if (newPassword !== confirmPassword) {
      setPasswordError("New password and confirmation do not match.");
      return;
    }

    setPasswordSaving(true);

    try {
      if (isDemoMode) {
        setTimeout(() => {
          setPasswordSuccess("Demo password changed successfully.");
          setCurrentPassword("");
          setNewPassword("");
          setConfirmPassword("");
          setPasswordSaving(false);
        }, 800);
        return;
      }

      const res = await userService.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: confirmPassword,
      });

      setPasswordSuccess(res.message || "Password updated successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      setPasswordError(err.message || "Failed to update password. Verify your current password.");
    } finally {
      setPasswordSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-white tracking-tight">Account & Security Settings</h1>
        <p className="text-xs sm:text-sm text-slate-400">
          Manage your personal details, credentials, and access keys.
        </p>
      </div>

      {/* Profile Details Card */}
      <Card className="border-slate-800 bg-slate-900/90 shadow-2xl">
        <CardHeader>
          <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
            <UserIcon className="w-4 h-4 text-blue-400" />
            <span>Profile Information</span>
          </CardTitle>
          <CardDescription className="text-xs text-slate-400">
            Update your display name and view account metadata.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {profileSuccess && (
            <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>{profileSuccess}</span>
            </div>
          )}

          <form onSubmit={handleUpdateProfile} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Display Name</label>
                <Input
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Your full name"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Email Address (Read-only)</label>
                <Input
                  disabled
                  value={user?.email || "user@sentinelvoice.io"}
                  className="bg-slate-950 text-slate-500 cursor-not-allowed"
                />
              </div>
            </div>

            <Button type="submit" size="sm" isLoading={profileSaving} className="bg-blue-600 hover:bg-blue-500 text-white text-xs">
              Save Profile Changes
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Password Change Card */}
      <Card className="border-slate-800 bg-slate-900/90 shadow-2xl">
        <CardHeader>
          <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
            <KeyRound className="w-4 h-4 text-purple-400" />
            <span>Security & Authentication</span>
          </CardTitle>
          <CardDescription className="text-xs text-slate-400">
            Change your account password. Password hashes are protected with Argon2id.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {passwordSuccess && (
            <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>{passwordSuccess}</span>
            </div>
          )}

          {passwordError && (
            <div className="p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              <span>{passwordError}</span>
            </div>
          )}

          <form onSubmit={handleChangePassword} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Current Password</label>
              <Input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="••••••••••••"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">New Password</label>
                <Input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••••••"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Confirm New Password</label>
                <Input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••••••"
                />
              </div>
            </div>

            <Button type="submit" size="sm" isLoading={passwordSaving} className="bg-blue-600 hover:bg-blue-500 text-white text-xs">
              Update Password
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}