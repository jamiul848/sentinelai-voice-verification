"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useDemoStore } from "@/store/useDemoStore";
import { AudioRecorder } from "@/components/voice/AudioRecorder";
import { useConsentStatus, useVerifyVoice, useVoiceProfile } from "@/hooks/useBiometrics";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDateTime, formatLatency, formatScore } from "@/lib/utils";
import { VerificationResponse } from "@/types";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  FileCheck,
  Mic,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

export default function VerificationPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);
  const { data: profile, isLoading: isProfileLoading } = useVoiceProfile();
  const { data: consent, isLoading: isConsentLoading } = useConsentStatus();
  const verifyMutation = useVerifyVoice();

  const [probeFile, setProbeFile] = useState<File | null>(null);
  const [result, setResult] = useState<VerificationResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleProbeRecorded = (file: File) => {
    setProbeFile(file);
    setResult(null);
    setErrorMsg(null);
  };

  const handleProbeReset = () => {
    setProbeFile(null);
    setResult(null);
    setErrorMsg(null);
  };

  const handleExecuteVerification = async () => {
    if (!probeFile) {
      setErrorMsg("Please record a spoken voice sample before initiating verification.");
      return;
    }

    setErrorMsg(null);
    setResult(null);

    try {
      const response = await verifyMutation.mutateAsync({ file: probeFile });
      setResult(response);
    } catch (err: any) {
      setErrorMsg(
        err.message ||
          "Verification service failed. Confirm your voice profile is active and audio quality is adequate."
      );
    }
  };

  const resetFlow = () => {
    setProbeFile(null);
    setResult(null);
    setErrorMsg(null);
  };

  const isCheckingPrerequisites = isProfileLoading || isConsentLoading;
  const hasActiveConsent = consent?.has_active_consent ?? false;
  const isProfileActive = profile?.status === "ACTIVE";

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-white tracking-tight">Voice Verification</h1>
          {isDemoMode && (
            <Badge variant="warning" className="gap-1 text-[10px]">
              <Sparkles className="w-3 h-3" /> DEMO
            </Badge>
          )}
        </div>
        <p className="text-xs sm:text-sm text-slate-400">
          Record a short voice sample to verify your identity against your enrolled voice profile.
        </p>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <Button size="sm" variant="outline" onClick={resetFlow} className="text-xs">
            Dismiss
          </Button>
        </div>
      )}

      {/* Prerequisite Check: Missing Profile */}
      {!isCheckingPrerequisites && !isProfileActive && !isDemoMode && (
        <Card className="border-amber-800/60 bg-slate-900/90 shadow-2xl">
          <CardHeader>
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 mb-2">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <CardTitle className="text-lg font-bold text-white">Active Voice Profile Required</CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Identity verification performs a 1:1 biometric comparison against a registered reference voiceprint.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs text-slate-300 leading-relaxed">
              {profile?.status === "REVOKED"
                ? "Your voice profile has been revoked and its biometric vector shredded. Verification is blocked until you re-enroll."
                : "No active voice profile was found for your account. Please complete enrollment by providing three reference speech samples."}
            </p>
            <div className="pt-2">
              <Link href="/enrollment">
                <Button className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs font-semibold px-6">
                  <Mic className="w-4 h-4" />
                  <span>{profile?.status === "REVOKED" ? "Re-enroll Voice" : "Begin Voice Enrollment"}</span>
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Prerequisite Check: Missing Consent */}
      {!isCheckingPrerequisites && isProfileActive && !hasActiveConsent && !isDemoMode && (
        <Card className="border-blue-800/60 bg-slate-900/90 shadow-2xl">
          <CardHeader>
            <div className="w-10 h-10 rounded-xl bg-blue-500/20 border border-blue-500/40 flex items-center justify-center text-blue-400 mb-2">
              <FileCheck className="w-5 h-5" />
            </div>
            <CardTitle className="text-lg font-bold text-white">Biometric Consent Needed</CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Under GDPR and BIPA requirements, active legal authorization is required before processing acoustic biometric vectors.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2">
            <Link href="/enrollment">
              <Button className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs font-semibold px-6">
                <span>Review & Authorize Consent</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Recording Stage (Permitted when profile is active and consent granted, or demo mode) */}
      {(isProfileActive || isDemoMode) && (hasActiveConsent || isDemoMode) && !result && (
        <Card className="border-slate-800 bg-slate-900/90 shadow-2xl">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white">Live Voice Probe</CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Speak clearly into your microphone for at least 1 second. The acoustic probe is evaluated in memory and never stored permanently.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <AudioRecorder
              sampleLabel="Verification Probe Utterance"
              minDurationSec={1.0}
              maxDurationSec={60.0}
              onRecordingComplete={handleProbeRecorded}
              onRecordingReset={handleProbeReset}
            />

            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
              <div className="text-xs text-slate-400">
                {probeFile ? (
                  <span className="text-emerald-400 font-medium flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Probe captured ({probeFile.name})
                  </span>
                ) : (
                  <span>Awaiting microphone capture...</span>
                )}
              </div>

              <Button
                onClick={handleExecuteVerification}
                disabled={!probeFile || verifyMutation.isPending}
                isLoading={verifyMutation.isPending}
                className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs font-semibold px-6 shadow-sm w-full sm:w-auto"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Verify Voiceprint</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Decision Result Card */}
      {result && (
        <div className="space-y-6 animate-in fade-in zoom-in-95 duration-200">
          <Card
            className={`shadow-2xl border ${
              result.decision === "MATCH"
                ? "border-emerald-600/60 bg-slate-900/95"
                : "border-red-600/60 bg-slate-900/95"
            }`}
          >
            <CardContent className="p-8 space-y-6 text-center">
              {/* Decision Badge & Icon */}
              <div
                className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto border ${
                  result.decision === "MATCH"
                    ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-400 glow-success"
                    : "bg-red-500/20 border-red-500/50 text-red-400 glow-danger"
                }`}
              >
                {result.decision === "MATCH" ? (
                  <ShieldCheck className="w-10 h-10" />
                ) : (
                  <ShieldAlert className="w-10 h-10" />
                )}
              </div>

              <div className="space-y-1">
                <span className="text-xs uppercase font-mono tracking-widest text-slate-400">
                  Acoustic Assessment Result
                </span>
                <h2
                  className={`text-3xl font-extrabold tracking-tight ${
                    result.decision === "MATCH" ? "text-emerald-400" : "text-red-400"
                  }`}
                >
                  {result.decision === "MATCH" ? "AUTHENTIC MATCH" : "NO MATCH / IMPOSTOR REJECTED"}
                </h2>
                <p className="text-xs text-slate-400 max-w-md mx-auto pt-1">
                  {result.decision === "MATCH"
                    ? "Claimant voice embedding meets calibrated similarity criteria against the enrolled reference profile."
                    : "Observed cosine similarity score fell below the active operating threshold. Identity could not be verified."}
                </p>
              </div>

              {/* Score & Threshold Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-2xl mx-auto p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-left text-xs">
                <div>
                  <span className="text-slate-400">Observed Similarity</span>
                  <p
                    className={`font-mono text-base font-bold mt-1 ${
                      result.decision === "MATCH" ? "text-emerald-400" : "text-red-400"
                    }`}
                  >
                    {formatScore(result.similarity_score)}
                  </p>
                </div>

                <div>
                  <span className="text-slate-400">Operating Threshold</span>
                  <p className="font-mono text-base font-bold text-slate-200 mt-1">
                    {formatScore(result.applied_threshold)}
                  </p>
                </div>

                <div>
                  <span className="text-slate-400">Evaluation Latency</span>
                  <p className="font-mono text-base font-bold text-blue-400 mt-1">
                    {formatLatency(result.processing_time_ms)}
                  </p>
                </div>

                <div>
                  <span className="text-slate-400">Threshold Version</span>
                  <p className="font-mono text-xs font-semibold text-slate-300 mt-2 truncate">
                    {result.threshold_version || "Default"}
                  </p>
                </div>
              </div>

              {/* Audit Event Reference */}
              <div className="text-[11px] text-slate-500 font-mono">
                Transaction ID: {result.verification_id} • Executed: {formatDateTime(result.timestamp)}
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                <Button onClick={resetFlow} variant="secondary" className="gap-2 text-xs w-full sm:w-auto">
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Verify Again</span>
                </Button>
                <Link href="/history" className="w-full sm:w-auto">
                  <Button variant="outline" className="text-xs w-full sm:w-auto gap-1.5">
                    <span>View Audit Logs</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
