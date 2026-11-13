"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { consentService } from "@/lib/api/services/consent.service";
import { useDemoStore } from "@/store/useDemoStore";
import { AudioRecorder } from "@/components/voice/AudioRecorder";
import { useEnrollVoice, useVoiceProfile } from "@/hooks/useBiometrics";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EnrollmentResponse } from "@/types";
import {
  AlertCircle,
  ArrowRight,
  FileCheck,
  Info,
  Lock,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";

export default function EnrollmentPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);
  const { data: existingProfile, isLoading: isCheckingProfile } = useVoiceProfile();
  const enrollMutation = useEnrollVoice();

  // Workflow steps: 1: Introduction & Consent -> 2: Record 3 Samples -> 3: Review & Submit -> 4: Complete
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [_hasConsent, setHasConsent] = useState(false);
  const [isGrantingConsent, setIsGrantingConsent] = useState(false);

  // Audio sample slots (minimum 3 required)
  const [recordedSamples, setRecordedSamples] = useState<(File | null)[]>([null, null, null]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [enrollmentResult, setEnrollmentResult] = useState<EnrollmentResponse | null>(null);

  // Check consent status on mount
  useEffect(() => {
    async function checkConsent() {
      if (isDemoMode) {
        setHasConsent(true);
        setStep(2);
        return;
      }
      try {
        const status = await consentService.getStatus();
        if (status.has_active_consent) {
          setHasConsent(true);
          setStep(2);
        }
      } catch {
        setHasConsent(false);
      }
    }
    checkConsent();
  }, [isDemoMode]);

  const handleGrantConsent = async () => {
    setErrorMsg(null);
    setIsGrantingConsent(true);
    try {
      if (!isDemoMode) {
        await consentService.grant({
          consent_type: "VOICE_BIOMETRIC_ENROLLMENT",
          consent_version: "1.0",
        });
      }
      setHasConsent(true);
      setStep(2);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to record biometric consent.");
    } finally {
      setIsGrantingConsent(false);
    }
  };

  const handleSampleRecorded = (index: number, file: File) => {
    setRecordedSamples((prev) => {
      const updated = [...prev];
      updated[index] = file;
      return updated;
    });
    setErrorMsg(null);
  };

  const handleSampleReset = (index: number) => {
    setRecordedSamples((prev) => {
      const updated = [...prev];
      updated[index] = null;
      return updated;
    });
  };

  const validSamples = recordedSamples.filter((s): s is File => s !== null);
  const allSamplesCaptured = validSamples.length >= 3;

  const handleSubmitEnrollment = async () => {
    if (validSamples.length < 3) {
      setErrorMsg("Enrollment requires all 3 distinct speech samples. Please complete missing recordings.");
      return;
    }

    setErrorMsg(null);

    try {
      const res = await enrollMutation.mutateAsync({
        files: validSamples,
        deviceInfo: "SentinelVoice W3C Web Audio Client",
      });
      setEnrollmentResult(res);
      setStep(4);
      // Clean up temporary audio references from memory
      setRecordedSamples([null, null, null]);
    } catch (err: any) {
      setErrorMsg(
        err.message || "Voiceprint enrollment failed. Verify audio quality and try again."
      );
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-white tracking-tight">Voiceprint Enrollment</h1>
          {isDemoMode && (
            <Badge variant="warning" className="gap-1 text-[10px]">
              <Sparkles className="w-3 h-3" /> DEMO
            </Badge>
          )}
        </div>
        <p className="text-xs sm:text-sm text-slate-400">
          Create your cryptographic voice template using 3 distinct speech recordings for ECAPA-TDNN centroid extraction.
        </p>
      </div>

      {/* Existing Active Profile Warning Banner */}
      {!isCheckingProfile && existingProfile && existingProfile.status === "ACTIVE" && step !== 4 && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/60 text-amber-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Info className="w-4 h-4 flex-shrink-0 text-amber-400" />
            <span>
              You already have an active voice profile (UUID: {existingProfile.id}). Submitting new enrollment will be rejected unless you re-enroll or revoke.
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/profile">
              <Button size="sm" variant="outline" className="text-xs border-amber-600/50 text-amber-300">
                Manage Profile
              </Button>
            </Link>
            <Link href="/verification">
              <Button size="sm" className="bg-amber-600 hover:bg-amber-500 text-black font-semibold text-xs">
                Go to Verification
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* Stepper Progress Indicator */}
      <div className="grid grid-cols-3 gap-2 p-2 rounded-xl bg-slate-900 border border-slate-800 text-xs font-medium">
        <div
          className={`flex items-center justify-center gap-2 py-2 rounded-lg transition-colors ${
            step >= 1 ? "bg-blue-600/20 text-blue-300 border border-blue-500/30" : "text-slate-500"
          }`}
        >
          <span className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold">
            1
          </span>
          <span>Consent</span>
        </div>
        <div
          className={`flex items-center justify-center gap-2 py-2 rounded-lg transition-colors ${
            step >= 2 && step <= 3 ? "bg-blue-600/20 text-blue-300 border border-blue-500/30" : "text-slate-500"
          }`}
        >
          <span className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold">
            2
          </span>
          <span>Capture 3 Samples</span>
        </div>
        <div
          className={`flex items-center justify-center gap-2 py-2 rounded-lg transition-colors ${
            step === 4 ? "bg-emerald-600/20 text-emerald-300 border border-emerald-500/30" : "text-slate-500"
          }`}
        >
          <span className="w-5 h-5 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[10px] font-bold">
            3
          </span>
          <span>Profile Created</span>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* STEP 1: Introduction & Legal Biometric Consent */}
      {step === 1 && (
        <Card className="border-slate-800 bg-slate-900/90 shadow-2xl">
          <CardHeader>
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 mb-2">
              <FileCheck className="w-5 h-5" />
            </div>
            <CardTitle className="text-lg font-bold text-white">Biometric Processing Consent & Disclosure</CardTitle>
            <CardDescription className="text-xs text-slate-400">
              In accordance with international privacy legislation (GDPR Art. 9, Illinois BIPA, and NIST SP 800-88 guidelines).
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3 text-xs text-slate-300 leading-relaxed">
              <p className="font-semibold text-white">
                Create your secure voice profile.
              </p>
              <p>
                Speaker verification analyzes acoustic biometric patterns in your speech to authenticate your identity. To create your reference voiceprint:
              </p>
              <ul className="list-disc pl-5 space-y-1.5 text-slate-400">
                <li>You will record three short spoken sentences (minimum 1.0 second each).</li>
                <li>Audio recordings are transformed into 192-dimensional ECAPA-TDNN neural embeddings.</li>
                <li>Voiceprint templates are stored using AES-256-GCM envelope encryption with per-profile DEKs.</li>
                <li>Raw audio files are processed in memory and never written to permanent disk storage.</li>
                <li>You maintain the permanent right to revoke your voice profile and cryptographically shred stored vectors at any time.</li>
              </ul>
            </div>

            <Button
              onClick={handleGrantConsent}
              isLoading={isGrantingConsent}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2.5"
            >
              Authorize Biometric Processing & Continue
            </Button>
          </CardContent>
        </Card>
      )}

      {/* STEP 2 & 3: Multi-Sample Recording & Review */}
      {(step === 2 || step === 3) && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-blue-950/30 border border-blue-800/40 text-xs text-blue-200 flex items-start gap-3">
            <Lock className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
            <span>
              <strong>Acoustic Protocol:</strong> Speak clearly at a normal conversational volume. Maintain a quiet background environment. Each sample must be between 1.0 and 60.0 seconds.
            </span>
          </div>

          <div className="space-y-4">
            <AudioRecorder
              sampleLabel="Utterance 1: Phonetic Baseline"
              minDurationSec={1.0}
              maxDurationSec={60.0}
              onRecordingComplete={(file) => handleSampleRecorded(0, file)}
              onRecordingReset={() => handleSampleReset(0)}
            />
            <AudioRecorder
              sampleLabel="Utterance 2: Dynamic Inflection"
              minDurationSec={1.0}
              maxDurationSec={60.0}
              onRecordingComplete={(file) => handleSampleRecorded(1, file)}
              onRecordingReset={() => handleSampleReset(1)}
            />
            <AudioRecorder
              sampleLabel="Utterance 3: Reference Anchor"
              minDurationSec={1.0}
              maxDurationSec={60.0}
              onRecordingComplete={(file) => handleSampleRecorded(2, file)}
              onRecordingReset={() => handleSampleReset(2)}
            />
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-xs text-slate-400">
              Samples Prepared:{" "}
              <strong className={allSamplesCaptured ? "text-emerald-400" : "text-white"}>
                {validSamples.length} of 3
              </strong>
              {allSamplesCaptured && " (Ready for neural centroid aggregation)"}
            </div>

            <Button
              onClick={handleSubmitEnrollment}
              disabled={!allSamplesCaptured || enrollMutation.isPending}
              isLoading={enrollMutation.isPending}
              className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs font-semibold px-6 w-full sm:w-auto"
            >
              <Upload className="w-4 h-4" />
              <span>Enroll Voiceprint</span>
            </Button>
          </div>
        </div>
      )}

      {/* STEP 4: Enrollment Success Confirmation */}
      {step === 4 && enrollmentResult && (
        <Card className="border-emerald-800/60 bg-slate-900/90 shadow-2xl text-center">
          <CardContent className="p-8 space-y-6">
            <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 mx-auto">
              <ShieldCheck className="w-8 h-8" />
            </div>

            <div className="space-y-2">
              <h2 className="text-2xl font-bold text-white">Voiceprint Successfully Enrolled</h2>
              <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto">
                Your 192D ECAPA-TDNN reference vector has been encrypted with AES-256-GCM and committed to PostgreSQL and secure biometric storage.
              </p>
            </div>

            <div className="max-w-md mx-auto grid grid-cols-2 gap-3 text-left text-xs p-4 rounded-xl bg-slate-950/80 border border-slate-800">
              <div>
                <span className="text-slate-400">Profile Identifier</span>
                <p className="font-mono text-white text-xs mt-0.5 truncate">{enrollmentResult.profile_id}</p>
              </div>
              <div>
                <span className="text-slate-400">Aggregated Utterances</span>
                <p className="font-semibold text-white mt-0.5">{enrollmentResult.sample_count} Recordings</p>
              </div>
              <div>
                <span className="text-slate-400">Pairwise Consistency</span>
                <p className="font-semibold text-emerald-400 mt-0.5 font-mono">
                  {enrollmentResult.mean_pairwise_similarity.toFixed(4)}
                </p>
              </div>
              <div>
                <span className="text-slate-400">Profile Status</span>
                <p className="font-semibold text-emerald-400 mt-0.5">{enrollmentResult.status}</p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <Link href="/verification" className="w-full sm:w-auto">
                <Button className="w-full sm:w-auto bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs font-semibold px-6">
                  <span>Proceed to Voice Verification</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </Link>
              <Link href="/profile" className="w-full sm:w-auto">
                <Button variant="secondary" className="w-full sm:w-auto text-xs">
                  View Profile Details
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
