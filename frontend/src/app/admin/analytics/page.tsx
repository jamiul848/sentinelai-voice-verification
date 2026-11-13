"use client";

import React from "react";
import { useDemoStore } from "@/store/useDemoStore";
import { DEMO_VERIFICATION_ACTIVITY_CHART } from "@/config/demo";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { VerificationChart } from "@/components/charts/VerificationChart";
import { CheckCircle2, Clock, ShieldAlert, Sparkles, Zap } from "lucide-react";

export default function AdminAnalyticsPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-white tracking-tight">Verification Analytics & Calibration</h1>
          {isDemoMode && (
            <Badge variant="warning" className="gap-1 text-[10px]">
              <Sparkles className="w-3 h-3" /> DEMO
            </Badge>
          )}
        </div>
        <p className="text-xs sm:text-sm text-slate-400">
          In-depth acoustic score distributions, equal error rate calibration provenance, and inference latencies.
        </p>
      </div>

      {/* Latency & Accuracy KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Mean Inference Latency</p>
              <p className="text-2xl font-bold text-blue-400 font-mono">1.18 s</p>
              <span className="text-[11px] text-slate-400">ECAPA-TDNN PyTorch</span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Clock className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Calibrated EER Operating Point</p>
              <p className="text-2xl font-bold text-emerald-400 font-mono">0.4059</p>
              <span className="text-[11px] text-slate-400">Equal Error Rate (1.25%)</span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Zap className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Genuine Claimants</p>
              <p className="text-2xl font-bold text-white">92.4%</p>
              <span className="text-[11px] text-emerald-400">Match Criteria Satisfied</span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Cross-Speaker Impostors</p>
              <p className="text-2xl font-bold text-red-400">7.6%</p>
              <span className="text-[11px] text-red-400">Deflected At Boundary</span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Verification Trends Chart */}
      <Card className="border-slate-800 bg-slate-900/80">
        <CardHeader>
          <CardTitle className="text-base font-semibold text-white">Fleet Verification Volume Over Time</CardTitle>
          <CardDescription className="text-xs text-slate-400">
            Temporal trajectory of genuine authorizations versus blocked zero-effort impostor trials.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4">
          <VerificationChart data={DEMO_VERIFICATION_ACTIVITY_CHART} />
        </CardContent>
      </Card>
    </div>
  );
}