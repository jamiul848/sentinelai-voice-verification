"use client";

import React, { useState } from "react";
import { useDemoStore } from "@/store/useDemoStore";
import { useAdminAnalytics } from "@/hooks/useAdmin";
import { formatLatency, formatPercent, formatScore } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { VerificationChart } from "@/components/charts/VerificationChart";
import {
  Activity,
  CheckCircle2,
  Clock,
  Info,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Zap,
} from "lucide-react";

export default function AdminAnalyticsPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);
  const [days, setDays] = useState<number>(7);

  const { data: analytics, isLoading, error, refetch, isFetching } = useAdminAnalytics(days);

  const chartData = analytics?.timeline?.map((item) => ({
    date: item.date,
    matches: item.matches,
    nonMatches: item.no_matches,
  })) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Verification Analytics & Performance</h1>
            {isDemoMode && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <Sparkles className="w-3 h-3" /> DEMO
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Real verification decisions, observed cosine score distributions, and ECAPA-TDNN latency analytics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Time window selector */}
          <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs">
            {[7, 14, 30, 90].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                  days === d ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                {d}D
              </button>
            ))}
          </div>

          <Button
            size="sm"
            variant="outline"
            onClick={() => refetch()}
            disabled={isFetching}
            className="gap-1.5 text-xs border-slate-700 bg-slate-900/60"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${isFetching ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* Accuracy vs Operational Match Rate Governance Banner */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
        <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <strong className="text-white">Operational Telemetry vs Evaluation Accuracy:</strong>
          <p className="text-slate-400 leading-relaxed">
            The operational MATCH rate reflects genuine claimant authentication decisions against enrolled voice centroids. True biometric accuracy (FAR, FRR, EER) is derived exclusively from standardized zero-effort impostor benchmark protocols (Phase 5E evaluation on LibriSpeech dev-clean).
          </p>
        </div>
      </div>

      {/* Latency & Decision KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Verifications */}
        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Total Attempts</p>
              <p className="text-2xl font-bold text-white font-mono">
                {isLoading ? "..." : analytics?.total_verifications ?? 0}
              </p>
              <span className="text-[11px] text-slate-500">Evaluated in last {days} days</span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Activity className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        {/* Operational Match Rate */}
        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Operational MATCH Rate</p>
              <p className="text-2xl font-bold text-emerald-400 font-mono">
                {isLoading ? "..." : `${analytics?.match_rate ?? 0}%`}
              </p>
              <span className="text-[11px] text-emerald-500/80">
                {analytics?.matches ?? 0} accepted authentic trials
              </span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        {/* Impostor Block Rate */}
        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">NO_MATCH Defense Rate</p>
              <p className="text-2xl font-bold text-red-400 font-mono">
                {isLoading ? "..." : `${analytics?.no_match_rate ?? 0}%`}
              </p>
              <span className="text-[11px] text-red-500/80">
                {analytics?.no_matches ?? 0} sub-threshold impostor blocks
              </span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        {/* Mean Latency */}
        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Mean Processing Latency</p>
              <p className="text-2xl font-bold text-blue-400 font-mono">
                {isLoading ? "..." : formatLatency(analytics?.average_latency_ms ?? 0)}
              </p>
              <span className="text-[11px] text-slate-500">ECAPA-TDNN extraction</span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <Clock className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Chart */}
      <Card className="border-slate-800 bg-slate-900/80">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <CardTitle className="text-base font-semibold text-white">Verification Decision Volume Timeline</CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Daily authentic MATCH decisions versus NO_MATCH impostor blocks over the last {days} days.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {chartData.length > 0 ? (
            <VerificationChart data={chartData} />
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-slate-500 text-xs gap-2">
              <Activity className="w-8 h-8 opacity-40" />
              <span>No verification decision events recorded in this time window.</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Active Threshold Reference Card */}
      {analytics?.active_threshold && (
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-emerald-400" />
              <span>Active Decision Threshold Benchmark</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              The neural boundary used by the verification engine to evaluate claimant speech.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
              <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-400">Version Tag</span>
                <p className="font-mono text-white text-xs font-semibold">{analytics.active_threshold.version_tag}</p>
              </div>
              <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-400">Operating Threshold (Cosine)</span>
                <p className="font-mono text-emerald-400 text-sm font-bold">
                  {formatScore(analytics.active_threshold.threshold_value, 6)}
                </p>
              </div>
              <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-400">Calibration Dataset</span>
                <p className="text-white text-xs">{analytics.active_threshold.calibration_dataset}</p>
              </div>
              <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-400">Optimization Goal</span>
                <p className="text-slate-300 text-xs">{analytics.active_threshold.calibration_criterion}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
