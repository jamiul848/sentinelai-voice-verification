"use client";

import React from "react";
import { useDemoStore } from "@/store/useDemoStore";
import { useActiveThreshold, useAdminSecurityEvents, useSystemHealthDetailed } from "@/hooks/useAdmin";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Cpu,
  Database,
  FolderLock,
  Globe,
  Info,
  Lock,
  RefreshCw,
  Server,
  Settings as SettingsIcon,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";

export default function AdminSettingsPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);
  const { data: health, isLoading: isHealthLoading, refetch: refetchHealth } = useSystemHealthDetailed();
  const { data: activeThresh, isLoading: isThreshLoading, refetch: refetchThresh } = useActiveThreshold();
  const { data: secEvents, isLoading: isSecLoading, refetch: refetchSec } = useAdminSecurityEvents();

  const handleRefreshAll = () => {
    refetchHealth();
    refetchThresh();
    refetchSec();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">System & Platform Governance</h1>
            {isDemoMode && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <Sparkles className="w-3 h-3" /> DEMO
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Read-only platform configuration metadata, model hyperparameters, and cluster operational bounds.
          </p>
        </div>

        <Button
          size="sm"
          variant="outline"
          onClick={handleRefreshAll}
          className="gap-1.5 text-xs border-slate-700 bg-slate-900/60"
        >
          <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
          <span>Refresh Configuration</span>
        </Button>
      </div>

      {/* Security Invariant Notice */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
        <Lock className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <strong className="text-white">Immutable Runtime Configuration Governance:</strong>
          <p className="text-slate-400 leading-relaxed">
            In compliance with zero-trust architectural boundaries, application secrets, master encryption keys, and environment variables are strictly immutable via client interfaces. All settings reflect authoritative backend server state.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Platform Identity */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
              <Globe className="w-4 h-4 text-blue-400" />
              <span>Platform Information</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Core runtime build and service metadata.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Service Name:</span>
              <span className="font-semibold text-white">{health?.service || "Sentinel Voice Application"}</span>
            </div>
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Release Version:</span>
              <span className="font-mono text-white">{health?.version || "0.1.0"}</span>
            </div>
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">API Prefix:</span>
              <span className="font-mono text-blue-300">/api/v1</span>
            </div>
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Interactive OpenAPI Docs:</span>
              <span className="font-mono text-emerald-400">/docs (Protected)</span>
            </div>
          </CardContent>
        </Card>

        {/* Neural Backbone Hyperparameters */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <span>Neural Embedding Architecture</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              SpeechBrain ECAPA-TDNN feature extractor parameters.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Model Backbone:</span>
              <span className="font-mono text-blue-300 truncate max-w-[200px]">
                {health?.ecapa_engine?.model_identifier || "speechbrain/spkrec-ecapa-voxceleb"}
              </span>
            </div>
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Embedding Dimension:</span>
              <span className="font-mono text-white">192-dimensional vector</span>
            </div>
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Audio Preprocessing:</span>
              <span className="font-mono text-slate-300">16,000 Hz Mono (RIFF/WAVE)</span>
            </div>
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">PyTorch Device:</span>
              <span className="font-mono text-purple-400 uppercase">{health?.ecapa_engine?.device || "CPU"}</span>
            </div>
          </CardContent>
        </Card>

        {/* Active Threshold Governance */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <span>Active Threshold Decision Boundary</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Operating boundary loaded dynamically from PostgreSQL.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Version Tag:</span>
              <span className="font-mono text-white font-semibold">{activeThresh?.version_tag || "Default"}</span>
            </div>
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Operating Point (Cosine):</span>
              <span className="font-mono text-emerald-400 font-bold">{activeThresh?.threshold_value ?? 0.405898}</span>
            </div>
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Provenance Dataset:</span>
              <span className="text-white">{activeThresh?.calibration_dataset || "LibriSpeech dev-clean"}</span>
            </div>
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Optimization Metric:</span>
              <span className="text-slate-300">{activeThresh?.calibration_criterion || "Equal Error Rate (EER)"}</span>
            </div>
          </CardContent>
        </Card>

        {/* Cryptographic Vault & Rate Limits */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
              <FolderLock className="w-4 h-4 text-purple-400" />
              <span>Cryptographic Storage & Quotas</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Envelope encryption and defense configurations.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Encryption Scheme:</span>
              <span className="font-mono text-purple-300">AES-256-GCM Envelope V2</span>
            </div>
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Rate Limiter Storage:</span>
              <span className="font-mono text-white">{secEvents?.rate_limiter?.backend || "in-memory (sliding-window)"}</span>
            </div>
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Verification Rate Limit:</span>
              <span className="font-mono text-blue-300">{secEvents?.rate_limiter?.rules?.biometrics_verify || "10/min"}</span>
            </div>
            <div className="flex justify-between p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400">Enrollment Rate Limit:</span>
              <span className="font-mono text-blue-300">{secEvents?.rate_limiter?.rules?.biometrics_enroll || "5/hour"}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

