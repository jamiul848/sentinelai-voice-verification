"use client";

import React, { useState } from "react";
import { useDemoStore } from "@/store/useDemoStore";
import { useAdminVoiceProfiles, useRevokeVoiceProfileAdmin } from "@/hooks/useAdmin";
import { AdminProfileListItem } from "@/types";
import { formatDateTime, formatScore } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  ShieldCheck,
  Sparkles,
  Trash2,
  XCircle,
} from "lucide-react";

export default function AdminVoiceProfilesPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "ACTIVE" | "REVOKED">("ALL");

  const { data, isLoading, error, refetch, isFetching } = useAdminVoiceProfiles({
    status: statusFilter === "ALL" ? undefined : statusFilter,
    limit: 100,
  });

  const revokeMutation = useRevokeVoiceProfileAdmin();

  // Revocation modal state
  const [targetProfile, setTargetProfile] = useState<AdminProfileListItem | null>(null);
  const [isRevokeDialogOpen, setIsRevokeDialogOpen] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const profiles = data?.items || [];

  const filteredProfiles = profiles.filter((p) => {
    const term = searchTerm.toLowerCase();
    return (
      p.id.toLowerCase().includes(term) ||
      p.user_id.toLowerCase().includes(term) ||
      (p.user_email && p.user_email.toLowerCase().includes(term)) ||
      (p.user_full_name && p.user_full_name.toLowerCase().includes(term))
    );
  });

  const handleOpenRevokeDialog = (profile: AdminProfileListItem) => {
    setActionError(null);
    setActionSuccess(null);
    setTargetProfile(profile);
    setIsRevokeDialogOpen(true);
  };

  const handleConfirmRevocation = async () => {
    if (!targetProfile) return;
    setActionError(null);
    try {
      await revokeMutation.mutateAsync(targetProfile.id);
      setActionSuccess(`Voice profile ${targetProfile.id} revoked and biometric vector shredded.`);
      setIsRevokeDialogOpen(false);
    } catch (err: any) {
      setActionError(err.response?.data?.message || err.message || "Failed to revoke voice profile.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Biometric Voiceprint Registry</h1>
            {isDemoMode && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <Sparkles className="w-3 h-3" /> DEMO
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Inspect enrolled acoustic identity centroids, intra-session consistency, and enforce cryptographic revocation.
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
          <span>Refresh Registry</span>
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

      {/* Security Governance Notice */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
        <Lock className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <strong className="text-white">Zero Raw Audio & Plaintext Vector Invariant:</strong>
          <p className="text-slate-400 leading-relaxed">
            In compliance with ISO/IEC 30107-3 and NIST SP 800-88, biometric vectors are encrypted at rest with AES-256-GCM and never exposed via frontend APIs. Administrative actions are restricted to lifecycle revocation and metadata audit inspection.
          </p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <Input
            placeholder="Search by user email, name, or profile UUID..."
            className="pl-9 text-xs h-9 bg-slate-950/80 border-slate-700"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
          <button
            onClick={() => setStatusFilter("ALL")}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              statusFilter === "ALL" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            All ({data?.total ?? 0})
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
            onClick={() => setStatusFilter("REVOKED")}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              statusFilter === "REVOKED" ? "bg-red-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            Shredded
          </button>
        </div>
      </div>

      {/* Profiles Table */}
      <Card className="border-slate-800 bg-slate-900/80">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Profile Identifier</TableHead>
                <TableHead>User Account</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Samples</TableHead>
                <TableHead>Centroid Consistency</TableHead>
                <TableHead>Model Identifier</TableHead>
                <TableHead>Created At</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-10 text-xs text-slate-500">
                    Loading biometric profile registry...
                  </TableCell>
                </TableRow>
              ) : filteredProfiles.length > 0 ? (
                filteredProfiles.map((p) => (
                  <TableRow key={p.id} className="hover:bg-slate-800/40">
                    <TableCell className="font-mono text-xs font-semibold text-white">
                      {p.id.slice(0, 13)}...
                    </TableCell>

                    <TableCell>
                      <div className="space-y-0.5">
                        <span className="font-medium text-white text-xs block">
                          {p.user_full_name || "Enrolled User"}
                        </span>
                        <span className="text-[11px] text-slate-400 font-mono block">
                          {p.user_email || p.user_id.slice(0, 8)}
                        </span>
                      </div>
                    </TableCell>

                    <TableCell>
                      {p.status === "ACTIVE" ? (
                        <Badge variant="success" className="text-[10px]">
                          ACTIVE
                        </Badge>
                      ) : (
                        <Badge variant="destructive" className="text-[10px]">
                          REVOKED
                        </Badge>
                      )}
                    </TableCell>

                    <TableCell className="text-xs text-slate-300 font-mono">
                      {p.sample_count} recordings
                    </TableCell>

                    <TableCell className="font-mono text-xs text-emerald-400 font-semibold">
                      {formatScore(p.mean_pairwise_similarity)}
                    </TableCell>

                    <TableCell className="font-mono text-[11px] text-blue-300 truncate max-w-[150px]">
                      {p.model_identifier}
                    </TableCell>

                    <TableCell className="text-xs text-slate-400 font-mono">
                      {formatDateTime(p.created_at)}
                    </TableCell>

                    <TableCell className="text-right">
                      {p.status === "ACTIVE" ? (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleOpenRevokeDialog(p)}
                          className="text-xs h-7 px-2.5 gap-1.5"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Revoke & Shred</span>
                        </Button>
                      ) : (
                        <span className="text-[11px] text-slate-500 italic">Vector Shredded</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-10 text-xs text-slate-500">
                    No voice profiles found matching filter criteria.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Revocation Confirmation Dialog */}
      <Dialog open={isRevokeDialogOpen} onOpenChange={setIsRevokeDialogOpen}>
        <DialogContent className="max-w-md bg-slate-900 border-slate-800 text-slate-100">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-red-400" />
              <span>Confirm Administrative Revocation</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-400">
              Revoke voiceprint for <strong className="text-white">{targetProfile?.user_email || targetProfile?.id}</strong>.
            </DialogDescription>
          </DialogHeader>

          <div className="p-3.5 rounded-lg bg-red-950/40 border border-red-800/60 text-xs text-red-200 space-y-1.5">
            <p>
              This operation executes a NIST SP 800-88 cryptographic disk overwrite of the stored speaker embedding file. The user will be blocked from voice verification until they grant fresh consent and complete new multi-sample enrollment.
            </p>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsRevokeDialogOpen(false)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleConfirmRevocation}
              isLoading={revokeMutation.isPending}
              className="bg-red-600 hover:bg-red-500 text-white text-xs gap-1.5"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Confirm Revocation & Shred</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

