 "use client";

import React, { useState } from "react";
import Link from "next/link";
import { biometricsService } from "@/lib/api/services/biometrics.service";
import { useDemoStore } from "@/store/useDemoStore";
import { AudioRecorder } from "@/components/voice/AudioRecorder";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDateTime, formatLatency, formatScore } from "@/lib/utils";
import { VerificationResponse } from "@/types";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

export default function VerificationPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  const [probeFile, setProbeFile] = useState<File | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [result, setResult] = useState<VerificationResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleProbeRecorded = (file: File) => {
    setProbeFile(file);
    setResult(null);
    setErrorMsg(null);
  };

  const handleExecuteVerification = async () => {
    if (!probeFile) {
      setErrorMsg("Please record an audio probe before submitting for verification.");
      return;
    }

    setIsVerifying(true);
    setErrorMsg(null);
    setResult(null);

    try {
      if (isDemoMode) {
        // Simulated verification for UI review
        setTimeout(() => {
          setResult({
            verification_id: "demo-verif-" + Date.now(),
            decision: "MATCH",
            is_match: true,
            similarity_score: 0.887451,
            applied_threshold: 0.405898,
            processing_time_ms: 1240.5,
            model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
            threshold_version: "v1.0.0-eer-calibrated",
            threshold_id: "77a80b12-9c31-4e78-8380-49658ec3429a",
            timestamp: new Date().toISOString(),
          });
          setIsVerifying(false);
        }, 1500);
        return;
      }

      const response = await biometricsService.verifyVoice(probeFile);
      setResult(response);
    } catch (err: any) {
      setErrorMsg(
        err.message ||
          "Verification service encountered an error. Confirm your voice profile is enrolled."
      );
    } finally {
      setIsVerifying(false);
    }
  };

  const resetFlow = () => {
    setProbeFile(null);
    setResult(null);
    setErrorMsg(null);
  };

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
          Provide a live acoustic voice probe to confirm claimant identity against the reference voiceprint.
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

      {/* Recording Stage */}
      {!result && (
        <Card className="border-slate-800 bg-slate-900/90 shadow-2xl">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white">Live Voice Probe</CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Speak clearly into your microphone for at least 3 seconds. The audio is streamed to the neural engine in memory and never persisted permanently.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <AudioRecorder
              sampleLabel="Verification Probe Utterance"
              minDurationSec={3}
              onRecordingComplete={handleProbeRecorded}
            />

            <div className="flex items-center justify-between pt-2">
              <div className="text-xs text-slate-400">
                {probeFile ? (
                  <span className="text-emerald-400 font-medium flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Probe captured ({probeFile.name})
                  </span>
                ) : (
                  <span>Awaiting microphone capture...</span>
                )}
              </div>

              <Button
                onClick={handleExecuteVerification}
                disabled={!probeFile || isVerifying}
                isLoading={isVerifying}
                className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs font-semibold px-6 shadow-sm"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Execute 1:1 Verification</span>
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
                  {result.decision === "MATCH" ? "AUTHENTIC MATCH" : "IMPOSTOR / NO MATCH"}
                </h2>
                <p className="text-xs text-slate-400 max-w-md mx-auto pt-1">
                  {result.decision === "MATCH"
                    ? "Claimant voice embedding meets calibrated similarity criteria against the enrolled reference profile."
                    : "Voice sample similarity score fell below the calibrated threshold. Claimant identity could not be verified."}
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
                  <span className="text-slate-400">Calibration Tag</span>
                  <p className="font-mono text-xs font-semibold text-slate-300 mt-2 truncate">
                    {result.threshold_version || "Default-EER"}
                  </p>
                </div>
              </div>

              {/* Audit Event Reference */}
              <div className="text-[11px] text-slate-500 font-mono">
                Transaction UUID: {result.verification_id} • Executed: {formatDateTime(result.timestamp)}
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