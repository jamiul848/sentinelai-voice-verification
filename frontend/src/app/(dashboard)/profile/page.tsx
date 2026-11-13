p"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { biometricsService } from "@/lib/api/services/biometrics.service";
import { consentService } from "@/lib/api/services/consent.service";
import { useDemoStore } from "@/store/useDemoStore";
import { DEMO_PROFILE } from "@/config/demo";
import { ConsentRecord, VoiceProfile } from "@/types";
import { formatDateTime, formatScore } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Mic,
  RotateCcw,
  Shield,
  ShieldCheck,
  Sparkles,
  Trash2,
  XCircle,
} from "lucide-react";

export default function ProfilePage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  const [profile, setProfile] = useState<VoiceProfile | null>(null);
  const [_consent, setConsent] = useState<ConsentRecord | null>(null);
  const [_isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Revocation modal state
  const [isRevokeOpen, setIsRevokeOpen] = useState(false);
  const [isRevoking, setIsRevoking] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      setErrorMsg(null);

      if (isDemoMode) {
        setProfile(DEMO_PROFILE);
        setConsent({
          id: "demo-consent-1",
          user_id: DEMO_PROFILE.user_id,
          consent_type: "VOICE_BIOMETRIC_ENROLLMENT",
          consent_version: "1.0",
          granted: true,
          created_at: "2026-11-10T08:30:00Z",
        });
        setIsLoading(false);
        return;
      }

      try {
        const [profileRes, consentRes] = await Promise.all([
          biometricsService.getProfile(),
          consentService.getStatus(),
        ]);
        setProfile(profileRes);
        setConsent(consentRes.record || null);
      } catch (err: any) {
        setErrorMsg(err.message || "Failed to load voice profile data.");
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [isDemoMode]);

  const handleRevokeConfirm = async () => {
    setIsRevoking(true);
    setErrorMsg(null);

    try {
      if (isDemoMode) {
        setTimeout(() => {
          setProfile((prev) => (prev ? { ...prev, status: "REVOKED", revoked_at: new Date().toISOString() } : null));
          setActionSuccess("Demo voice profile marked as revoked and erased.");
          setIsRevoking(false);
          setIsRevokeOpen(false);
        }, 1000);
        return;
      }

      const res = await biometricsService.revokeProfile();
      setActionSuccess(res.message || "Voice profile permanently revoked and biometric vector shredded.");
      setProfile((prev) => (prev ? { ...prev, status: "REVOKED", revoked_at: new Date().toISOString() } : null));
      setIsRevokeOpen(false);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to revoke voice profile.");
    } finally {
      setIsRevoking(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-white tracking-tight">Voice Biometric Profile</h1>
          {isDemoMode && (
            <Badge variant="warning" className="gap-1 text-[10px]">
              <Sparkles className="w-3 h-3" /> DEMO
            </Badge>
          )}
        </div>
        <p className="text-xs sm:text-sm text-slate-400">
          Manage your enrolled acoustic identity, inspect compliance consent, or cryptographically shred biometric data.
        </p>
      </div>

      {actionSuccess && (
        <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2.5">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Profile Card */}
      <Card className="border-slate-800 bg-slate-900/90 shadow-2xl">
        <CardHeader className="flex flex-row items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-400" />
              <span>Reference Voiceprint</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Aggregated speaker centroid generated via ECAPA-TDNN temporal neural delay network.
            </CardDescription>
          </div>

          <div>
            {profile?.status === "ACTIVE" ? (
              <Badge variant="success" className="gap-1 text-xs">
                <ShieldCheck className="w-3.5 h-3.5" /> ACTIVE
              </Badge>
            ) : profile?.status === "REVOKED" ? (
              <Badge variant="destructive" className="gap-1 text-xs">
                <XCircle className="w-3.5 h-3.5" /> REVOKED
              </Badge>
            ) : (
              <Badge variant="outline" className="text-xs text-amber-400 border-amber-500/30">
                NOT ENROLLED
              </Badge>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {profile ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1.5">
                <span className="text-slate-400">Profile Identifier</span>
                <p className="font-mono text-white text-sm font-semibold truncate">{profile.id}</p>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1.5">
                <span className="text-slate-400">Enrolled Utterance Count</span>
                <p className="text-white text-sm font-semibold">{profile.sample_count} speech recordings</p>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1.5">
                <span className="text-slate-400">Intra-Session Consistency</span>
                <p className="font-mono text-emerald-400 text-sm font-semibold">
                  {formatScore(profile.mean_pairwise_similarity)} (Centroid Stability)
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1.5">
                <span className="text-slate-400">Neural Recognition Backbone</span>
                <p className="font-mono text-blue-300 text-sm font-semibold truncate">
                  {profile.model_identifier}
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1.5">
                <span className="text-slate-400">Enrollment Timestamp</span>
                <p className="text-slate-200 text-xs">{formatDateTime(profile.created_at)}</p>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1.5">
                <span className="text-slate-400">Last Modified</span>
                <p className="text-slate-200 text-xs">{formatDateTime(profile.updated_at)}</p>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-400 space-y-4">
              <p>No active voice profile discovered for this account.</p>
              <Link href="/enrollment">
                <Button className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs">
                  <Mic className="w-3.5 h-3.5" />
                  <span>Start Voice Enrollment</span>
                </Button>
              </Link>
            </div>
          )}

          {/* Biometric Security & Consent Ledger */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white flex items-center gap-2">
                <Lock className="w-4 h-4 text-blue-400" />
                Biometric Encryption & Governance
              </span>
              <span className="text-xs font-mono text-emerald-400">AES-256-GCM Envelope V2</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Biometric embeddings are encrypted at rest with randomly generated Data Encryption Keys (DEKs) wrapped by the master application KEK. Raw acoustic vectors are never stored in plaintext columns.
            </p>
          </div>

          {/* Action Row */}
          {profile && profile.status === "ACTIVE" && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-800">
              <Link href="/enrollment">
                <Button variant="secondary" size="sm" className="gap-2 text-xs">
                  <RotateCcw className="w-3.5 h-3.5 text-blue-400" />
                  <span>Re-enroll Voiceprint</span>
                </Button>
              </Link>

              <Button
                variant="destructive"
                size="sm"
                onClick={() => setIsRevokeOpen(true)}
                className="gap-2 text-xs"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Revoke & Shred Voiceprint</span>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Revocation Confirmation Modal */}
      <Dialog open={isRevokeOpen} onOpenChange={setIsRevokeOpen}>
        <DialogHeader>
          <div className="w-10 h-10 rounded-full bg-red-500/20 text-red-400 flex items-center justify-center mb-2">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <DialogTitle>Confirm Biometric Profile Revocation</DialogTitle>
          <DialogDescription>
            This action will permanently delete your voiceprint. The backend will execute a multi-pass NIST SP 800-88 cryptographic overwrite across on-disk encrypted containers before unlinking database metadata.
          </DialogDescription>
        </DialogHeader>

        <div className="p-3 rounded-lg bg-red-950/40 border border-red-900/60 text-xs text-red-300">
          <strong>Warning:</strong> You will not be able to perform 1:1 speaker verification until you complete a new voice enrollment.
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => setIsRevokeOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleRevokeConfirm}
            isLoading={isRevoking}
          >
            Permanently Shred Biometric Data
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}