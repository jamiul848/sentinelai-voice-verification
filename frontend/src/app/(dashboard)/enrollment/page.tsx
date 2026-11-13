"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { consentService } from "@/lib/api/services/consent.service";
import { biometricsService } from "@/lib/api/services/biometrics.service";
import { useDemoStore } from "@/store/useDemoStore";
import { AudioRecorder } from "@/components/voice/AudioRecorder";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  AlertCircle,
  ArrowRight,
  FileCheck,
  Lock,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";

export default function EnrollmentPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  // Stepper state: 1: Consent -> 2: Record Samples -> 3: Complete
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [_hasConsent, setHasConsent] = useState(false);
  const [isGrantingConsent, setIsGrantingConsent] = useState(false);

  // Audio files: Backend requires at least 3 audio recordings
  const [recordedFiles, setRecordedFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [enrollmentResult, setEnrollmentResult] = useState<any | null>(null);

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
        // If 404 or ungranted, remain on step 1
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
    setRecordedFiles((prev) => {
      const next = [...prev];
      next[index] = file;
      return next;
    });
  };

  const handleSubmitEnrollment = async () => {
    if (recordedFiles.filter(Boolean).length < 3) {
      setErrorMsg("Please record all 3 required speech samples before submitting.");
      return;
    }

    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      if (isDemoMode) {
        // Simulated enrollment response for demo inspection
        setTimeout(() => {
          setEnrollmentResult({
            profile_id: "demo-prof-" + Date.now(),
            sample_count: 3,
            mean_pairwise_similarity: 0.892,
            model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
            status: "ACTIVE",
          });
          setStep(3);
          setIsSubmitting(false);
        }, 1200);
        return;
      }

      const res = await biometricsService.enrollVoice(
        recordedFiles.filter(Boolean),
        "SentinelVoice Web Client (W3C Audio)"
      );
      setEnrollmentResult(res);
      setStep(3);
    } catch (err: any) {
      setErrorMsg(err.message || "Voice enrollment failed. Please re-record your samples.");
    } finally {
      setIsSubmitting(false);
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
          Enroll your acoustic reference model using three high-fidelity speech recordings.
        </p>
      </div>

      {/* Stepper Progress */}
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
            step >= 2 ? "bg-blue-600/20 text-blue-300 border border-blue-500/30" : "text-slate-500"
          }`}
        >
          <span className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold">
            2
          </span>
          <span>Record (3 Samples)</span>
        </div>
        <div
          className={`flex items-center justify-center gap-2 py-2 rounded-lg transition-colors ${
            step === 3 ? "bg-emerald-600/20 text-emerald-300 border border-emerald-500/30" : "text-slate-500"
          }`}
        >
          <span className="w-5 h-5 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[10px] font-bold">
            3
          </span>
          <span>Verification Ready</span>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* STEP 1: Consent Confirmation */}
      {step === 1 && (
        <Card className="border-slate-800 bg-slate-900/90 shadow-2xl">
          <CardHeader>
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 mb-2">
              <FileCheck className="w-5 h-5" />
            </div>
            <CardTitle className="text-lg font-bold text-white">Biometric Processing Consent</CardTitle>
            <CardDescription className="text-xs text-slate-400">
              In compliance with international data privacy laws (GDPR Art. 9, Illinois BIPA, and NIST guidelines).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3 text-xs text-slate-300 leading-relaxed">
              <p>
                To provide speaker verification capabilities, Sentinel Voice processes your voice recordings to generate a 192-dimensional numerical embedding vector.
              </p>
              <ul className="list-disc pl-5 space-y-1 text-slate-400">
                <li>Recordings are analyzed using pretrained ECAPA-TDNN neural networks.</li>
                <li>Biometric embeddings are encrypted with AES-256-GCM envelope cryptography.</li>
                <li>Your voiceprint is strictly used for 1:1 identity verification when requested by you.</li>
                <li>You maintain the permanent right to delete and cryptographically shred your profile (NIST SP 800-88).</li>
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

      {/* STEP 2: Acoustic Recording (3 Samples) */}
      {step === 2 && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-blue-950/30 border border-blue-800/40 text-xs text-blue-200 flex items-start gap-3">
            <Lock className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
            <span>
              <strong>Enrollment Protocol:</strong> Record 3 distinct spoken sentences (minimum 3 seconds each). Maintain a quiet environment and consistent distance from the microphone.
            </span>
          </div>

          <div className="space-y-4">
            <AudioRecorder
              sampleLabel="Utterance 1: Phonetic Baseline"
              minDurationSec={3}
              onRecordingComplete={(file) => handleSampleRecorded(0, file)}
            />
            <AudioRecorder
              sampleLabel="Utterance 2: Dynamic Inflection"
              minDurationSec={3}
              onRecordingComplete={(file) => handleSampleRecorded(1, file)}
            />
            <AudioRecorder
              sampleLabel="Utterance 3: Reference Anchor"
              minDurationSec={3}
              onRecordingComplete={(file) => handleSampleRecorded(2, file)}
            />
          </div>

          <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-xs text-slate-400">
              Samples Recorded:{" "}
              <strong className="text-white">
                {recordedFiles.filter(Boolean).length} of 3
              </strong>
            </div>

            <Button
              onClick={handleSubmitEnrollment}
              disabled={recordedFiles.filter(Boolean).length < 3}
              isLoading={isSubmitting}
              className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs font-semibold px-6"
            >
              <Upload className="w-4 h-4" />
              <span>Generate Biometric Centroid</span>
            </Button>
          </div>
        </div>
      )}

      {/* STEP 3: Enrollment Success */}
      {step === 3 && (
        <Card className="border-emerald-800/60 bg-slate-900/90 shadow-2xl text-center">
          <CardContent className="p-8 space-y-6">
            <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 mx-auto">
              <ShieldCheck className="w-8 h-8" />
            </div>

            <div className="space-y-2">
              <h2 className="text-2xl font-bold text-white">Voiceprint Successfully Enrolled</h2>
              <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto">
                Your 192D ECAPA-TDNN reference vector has been encrypted and committed to the secure biometric vault.
              </p>
            </div>

            <div className="max-w-md mx-auto grid grid-cols-2 gap-3 text-left text-xs p-4 rounded-xl bg-slate-950/80 border border-slate-800">
              <div>
                <span className="text-slate-400">Enrolled Samples</span>
                <p className="font-semibold text-white mt-0.5">{enrollmentResult?.sample_count || 3} Utterances</p>
              </div>
              <div>
                <span className="text-slate-400">Pairwise Consistency</span>
                <p className="font-semibold text-emerald-400 mt-0.5 font-mono">
                  {enrollmentResult?.mean_pairwise_similarity?.toFixed(4) || "0.8842"}
                </p>
              </div>
              <div>
                <span className="text-slate-400">Encryption Method</span>
                <p className="font-semibold text-white mt-0.5">AES-256-GCM Envelope</p>
              </div>
              <div>
                <span className="text-slate-400">Status</span>
                <p className="font-semibold text-emerald-400 mt-0.5">ACTIVE</p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <Link href="/verification" className="w-full sm:w-auto">
                <Button className="w-full sm:w-auto bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs font-semibold px-6">
                  <span>Proceed to Voice Verification</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </Link>
              <Link href="/dashboard" className="w-full sm:w-auto">
                <Button variant="secondary" className="w-full sm:w-auto text-xs">
                  Dashboard
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
