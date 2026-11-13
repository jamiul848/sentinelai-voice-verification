"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useDemoStore } from "@/store/useDemoStore";
import {
  useConsentStatus,
  useReEnrollVoice,
  useRevokeVoiceProfile,
  useVoiceProfile,
} from "@/hooks/useBiometrics";
import { AudioRecorder } from "@/components/voice/AudioRecorder";
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
import { formatDateTime, formatScore } from "@/lib/utils";
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
  Upload,
  XCircle,
} from "lucide-react";

export default function ProfilePage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);
  const { data: profile, isLoading, error: profileError } = useVoiceProfile();
  const { data: consent } = useConsentStatus();
  const revokeMutation = useRevokeVoiceProfile();
  const reEnrollMutation = useReEnrollVoice();

  // Revocation modal state
  const [isRevokeOpen, setIsRevokeOpen] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Re-enrollment modal / panel state
  const [isReEnrollOpen, setIsReEnrollOpen] = useState(false);
  const [reEnrollSamples, setReEnrollSamples] = useState<(File | null)[]>([null, null, null]);

  const handleRevokeConfirm = async () => {
    setActionError(null);
    setActionSuccess(null);

    try {
      const res = await revokeMutation.mutateAsync();
      setActionSuccess(res.message || "Voice profile permanently revoked and biometric vector shredded.");
      setIsRevokeOpen(false);
    } catch (err: any) {
      setActionError(err.message || "Failed to revoke voice profile.");
    }
  };

  const handleReEnrollSampleRecorded = (index: number, file: File) => {
    setReEnrollSamples((prev) => {
      const updated = [...prev];
      updated[index] = file;
      return updated;
    });
    setActionError(null);
  };

  const handleReEnrollSampleReset = (index: number) => {
    setReEnrollSamples((prev) => {
      const updated = [...prev];
      updated[index] = null;
      return updated;
    });
  };

  const validReEnrollSamples = reEnrollSamples.filter((s): s is File => s !== null);

  const handleExecuteReEnrollment = async () => {
    if (validReEnrollSamples.length < 3) {
      setActionError("Please record all 3 required utterances before submitting re-enrollment.");
      return;
    }

    setActionError(null);
    try {
      const res = await reEnrollMutation.mutateAsync({ files: validReEnrollSamples });
      setActionSuccess(res.message || "Voiceprint re-enrollment completed successfully.");
      setIsReEnrollOpen(false);
      setReEnrollSamples([null, null, null]);
    } catch (err: any) {
      setActionError(err.message || "Re-enrollment failed. Verify audio quality.");
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

      {(actionError || profileError) && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{actionError || profileError?.message}</span>
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
              Aggregated speaker centroid generated via ECAPA-TDNN neural embedding architecture.
            </CardDescription>
          </div>

          <div>
            {isLoading ? (
              <span className="text-xs text-slate-500 animate-pulse">Loading profile...</span>
            ) : profile?.status === "ACTIVE" ? (
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
          {profile?.status === "ACTIVE" ? (
            <div className="space-y-6">
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
                  <span className="text-slate-400">Biometric Consent Status</span>
                  <p className="text-slate-200 text-xs flex items-center gap-1.5">
                    {consent?.has_active_consent ? (
                      <span className="text-emerald-400 font-medium">Authorized (Active)</span>
                    ) : (
                      <span className="text-amber-400 font-medium">Pending Authorization</span>
                    )}
                  </p>
                </div>
              </div>

              {/* Sample Acoustic Metrics Breakdown */}
              {profile.enrollment_records && profile.enrollment_records.length > 0 && (
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                  <span className="text-xs font-semibold text-white">Constituent Utterance Telemetry</span>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {profile.enrollment_records.map((sample, idx) => (
                      <div key={idx} className="p-3 rounded-lg bg-slate-900 border border-slate-800/80 text-[11px] space-y-1">
                        <span className="text-slate-400 font-medium">Utterance #{idx + 1}</span>
                        <div className="flex justify-between text-slate-300">
                          <span>Duration:</span>
                          <span className="font-mono">{sample.duration_sec.toFixed(2)}s</span>
                        </div>
                        <div className="flex justify-between text-slate-300">
                          <span>Format:</span>
                          <span className="font-mono">{sample.audio_format}</span>
                        </div>
                        <div className="flex justify-between text-slate-300">
                          <span>Peak Amp:</span>
                          <span className="font-mono">{sample.peak_amplitude.toFixed(3)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-800">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsReEnrollOpen(true)}
                  className="gap-2 text-xs w-full sm:w-auto"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-blue-400" />
                  <span>Re-enroll Voiceprint</span>
                </Button>

                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setIsRevokeOpen(true)}
                  className="gap-2 text-xs w-full sm:w-auto"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Revoke & Shred Voiceprint</span>
                </Button>
              </div>
            </div>
          ) : profile?.status === "REVOKED" ? (
            <div className="p-8 text-center text-xs text-slate-400 space-y-4">
              <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 mx-auto">
                <XCircle className="w-6 h-6" />
              </div>
              <p className="max-w-md mx-auto text-slate-300">
                Your previous voice profile has been revoked and its biometric vector shredded in accordance with NIST SP 800-88. Speaker verification requires a valid active profile and consent.
              </p>
              <Link href="/enrollment">
                <Button className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs font-semibold px-6">
                  <Mic className="w-3.5 h-3.5" />
                  <span>Create New Voice Profile</span>
                </Button>
              </Link>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-400 space-y-4">
              <p>Your voice profile has not been created.</p>
              <Link href="/enrollment">
                <Button className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs font-semibold px-6">
                  <Mic className="w-3.5 h-3.5" />
                  <span>Begin Voice Enrollment</span>
                </Button>
              </Link>
            </div>
          )}

          {/* Biometric Security & Cryptography Info */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white flex items-center gap-2">
                <Lock className="w-4 h-4 text-blue-400" />
                Biometric Envelope Cryptography
              </span>
              <span className="text-xs font-mono text-emerald-400">AES-256-GCM Envelope V2</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Biometric embeddings are encrypted at rest with randomly generated Data Encryption Keys (DEKs) wrapped by the master application KEK. Raw acoustic vectors are never stored in plaintext database columns.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Revocation Confirmation Dialog */}
      <Dialog open={isRevokeOpen} onOpenChange={setIsRevokeOpen}>
        <DialogHeader>
          <div className="w-10 h-10 rounded-full bg-red-500/20 border border-red-500/30 flex items-center justify-center text-red-400 mb-2">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <DialogTitle>Confirm Voice Profile Revocation & Shredding</DialogTitle>
          <DialogDescription className="text-xs text-slate-400 leading-relaxed">
            Revoking your voice profile will prevent future speaker verification using this profile. This operation also triggers the backend biometric deletion process, executing multi-pass cryptographic erasure (NIST SP 800-88) of the stored vector container.
          </DialogDescription>
        </DialogHeader>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="ghost"
            onClick={() => setIsRevokeOpen(false)}
            className="text-xs"
            disabled={revokeMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleRevokeConfirm}
            isLoading={revokeMutation.isPending}
            className="text-xs gap-1.5"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Confirm Permanent Revocation</span>
          </Button>
        </DialogFooter>
      </Dialog>

      {/* Re-Enrollment Modal Dialog */}
      <Dialog open={isReEnrollOpen} onOpenChange={setIsReEnrollOpen}>
        <DialogHeader>
          <div className="w-10 h-10 rounded-full bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400 mb-2">
            <RotateCcw className="w-5 h-5" />
          </div>
          <DialogTitle>Re-enroll Reference Voiceprint</DialogTitle>
          <DialogDescription className="text-xs text-slate-400 leading-relaxed">
            Re-enrollment deactivates your prior profile, cryptographically shreds the old vector container, and calculates a new 192D centroid from 3 fresh recordings.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <AudioRecorder
            sampleLabel="Sample 1 of 3: Phonetic Baseline"
            minDurationSec={1.0}
            maxDurationSec={60.0}
            onRecordingComplete={(file) => handleReEnrollSampleRecorded(0, file)}
            onRecordingReset={() => handleReEnrollSampleReset(0)}
          />
          <AudioRecorder
            sampleLabel="Sample 2 of 3: Dynamic Inflection"
            minDurationSec={1.0}
            maxDurationSec={60.0}
            onRecordingComplete={(file) => handleReEnrollSampleRecorded(1, file)}
            onRecordingReset={() => handleReEnrollSampleReset(1)}
          />
          <AudioRecorder
            sampleLabel="Sample 3 of 3: Reference Anchor"
            minDurationSec={1.0}
            maxDurationSec={60.0}
            onRecordingComplete={(file) => handleReEnrollSampleRecorded(2, file)}
            onRecordingReset={() => handleReEnrollSampleReset(2)}
          />
        </div>

        <DialogFooter className="flex items-center justify-between gap-2 sm:gap-0 pt-2 border-t border-slate-800">
          <span className="text-xs text-slate-400">
            Recorded: {validReEnrollSamples.length} of 3
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              onClick={() => setIsReEnrollOpen(false)}
              className="text-xs"
              disabled={reEnrollMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleExecuteReEnrollment}
              disabled={validReEnrollSamples.length < 3 || reEnrollMutation.isPending}
              isLoading={reEnrollMutation.isPending}
              className="bg-blue-600 hover:bg-blue-500 text-white text-xs gap-1.5"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Submit Re-enrollment</span>
            </Button>
          </div>
        </DialogFooter>
      </Dialog>
    </div>
  );
}
