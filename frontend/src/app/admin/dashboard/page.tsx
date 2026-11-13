"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuthStore } from "@/store/useAuthStore";
import { useDemoStore } from "@/store/useDemoStore";
import { useAdminAnalytics, useAdminOverview } from "@/hooks/useAdmin";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { VerificationChart } from "@/components/charts/VerificationChart";
import { formatDateTime } from "@/lib/utils";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Database,
  FileText,
  Lock,
  RefreshCw,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sparkles,
  Users,
  XCircle,
} from "lucide-react";

export default function AdminDashboardPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);
  const currentUser = useAuthStore((s) => s.user);

  const [days, setDays] = useState<number>(7);
  const { data: overview, isLoading, error, refetch, isFetching } = useAdminOverview();
  const { data: analytics } = useAdminAnalytics(days);

  const chartData = analytics?.timeline?.map((item) => ({
    date: item.date,
    matches: item.matches,
    nonMatches: item.no_matches,
  })) || [];

  return (
    <div className="space-y-6">
      {/* Welcome & System Status Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-blue-950/40 border border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Fleet Operations & Governance</h1>
            {isDemoMode && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <Sparkles className="w-3 h-3" /> DEMO
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Authenticated Administrator: <strong className="text-white">{currentUser?.full_name || "Admin Officer"}</strong> ({currentUser?.roles?.join(", ") || "ADMIN"})
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
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
          <Link href="/admin/system-health">
            <Button size="sm" variant="outline" className="gap-1.5 text-xs border-slate-700 bg-slate-900/60">
              <Activity className="w-3.5 h-3.5 text-blue-400" />
              <span>Probes</span>
            </Button>
          </Link>
          <Link href="/admin/thresholds">
            <Button size="sm" className="bg-blue-600 hover:bg-blue-500 text-white gap-1.5 text-xs">
              <Sliders className="w-3.5 h-3.5" />
              <span>Thresholds</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* Error Callout */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/30 border border-red-800/60 text-xs text-red-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>Failed to synchronize admin overview statistics. Authenticate with an administrative account.</span>
          </div>
          <Button size="sm" variant="outline" onClick={() => refetch()} className="text-xs h-7">
            Retry
          </Button>
        </div>
      )}

      {/* Platform Statistics (8 Cards) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        {/* 1. Total Registered Users */}
        <Card className="border-slate-800 bg-slate-900/80 p-3.5 space-y-1">
          <span className="text-[11px] text-slate-400 uppercase font-mono tracking-wider">Total Users</span>
          <p className="text-xl font-bold text-white font-mono">{isLoading ? "..." : overview?.users?.total ?? 0}</p>
          <span className="text-[10px] text-slate-500 block">Registered fleet</span>
        </Card>

        {/* 2. Active Users */}
        <Card className="border-slate-800 bg-slate-900/80 p-3.5 space-y-1">
          <span className="text-[11px] text-slate-400 uppercase font-mono tracking-wider">Active Users</span>
          <p className="text-xl font-bold text-emerald-400 font-mono">{isLoading ? "..." : overview?.users?.active ?? 0}</p>
          <span className="text-[10px] text-emerald-500/80 block">Authorized</span>
        </Card>

        {/* 3. Inactive Users */}
        <Card className="border-slate-800 bg-slate-900/80 p-3.5 space-y-1">
          <span className="text-[11px] text-slate-400 uppercase font-mono tracking-wider">Suspended</span>
          <p className="text-xl font-bold text-amber-400 font-mono">{isLoading ? "..." : overview?.users?.inactive ?? 0}</p>
          <span className="text-[10px] text-amber-500/80 block">Deactivated</span>
        </Card>

        {/* 4. Active Profiles */}
        <Card className="border-slate-800 bg-slate-900/80 p-3.5 space-y-1">
          <span className="text-[11px] text-slate-400 uppercase font-mono tracking-wider">Active Voice</span>
          <p className="text-xl font-bold text-purple-400 font-mono">{isLoading ? "..." : overview?.voice_profiles?.active ?? 0}</p>
          <span className="text-[10px] text-purple-400/80 block">Enrolled centroids</span>
        </Card>

        {/* 5. Revoked Profiles */}
        <Card className="border-slate-800 bg-slate-900/80 p-3.5 space-y-1">
          <span className="text-[11px] text-slate-400 uppercase font-mono tracking-wider">Shredded</span>
          <p className="text-xl font-bold text-red-400 font-mono">{isLoading ? "..." : overview?.voice_profiles?.revoked ?? 0}</p>
          <span className="text-[10px] text-red-500/80 block">NIST SP 800-88</span>
        </Card>

        {/* 6. Total Verifications */}
        <Card className="border-slate-800 bg-slate-900/80 p-3.5 space-y-1">
          <span className="text-[11px] text-slate-400 uppercase font-mono tracking-wider">Verifications</span>
          <p className="text-xl font-bold text-blue-400 font-mono">{isLoading ? "..." : overview?.verifications?.total ?? 0}</p>
          <span className="text-[10px] text-blue-400/80 block">Evaluated probes</span>
        </Card>

        {/* 7. MATCH Decisions */}
        <Card className="border-slate-800 bg-slate-900/80 p-3.5 space-y-1">
          <span className="text-[11px] text-slate-400 uppercase font-mono tracking-wider">Matches</span>
          <p className="text-xl font-bold text-emerald-400 font-mono">{isLoading ? "..." : overview?.verifications?.matches ?? 0}</p>
          <span className="text-[10px] text-emerald-400/80 block">
            {overview?.verifications?.match_rate ? `${overview.verifications.match_rate}%` : "0%"} rate
          </span>
        </Card>

        {/* 8. NO_MATCH Decisions */}
        <Card className="border-slate-800 bg-slate-900/80 p-3.5 space-y-1">
          <span className="text-[11px] text-slate-400 uppercase font-mono tracking-wider">Rejections</span>
          <p className="text-xl font-bold text-red-400 font-mono">{isLoading ? "..." : overview?.verifications?.no_matches ?? 0}</p>
          <span className="text-[10px] text-red-400/80 block">Impostors blocked</span>
        </Card>
      </div>

      {/* Analytics Chart & Cluster Subsystems Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 border-slate-800 bg-slate-900/80">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-base font-semibold text-white">Platform Verification Volume</CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Daily aggregation of claimant evaluations across all platform clients.
              </CardDescription>
            </div>
            <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
              <button
                onClick={() => setDays(7)}
                className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                  days === 7 ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                7 Days
              </button>
              <button
                onClick={() => setDays(30)}
                className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                  days === 30 ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                30 Days
              </button>
            </div>
          </CardHeader>
          <CardContent className="pt-4">
            {chartData.length > 0 ? (
              <VerificationChart data={chartData} />
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-slate-500 text-xs gap-2">
                <Activity className="w-8 h-8 opacity-40" />
                <span>No verification events recorded in this time window.</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Cluster Subsystems Status */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white">Cluster Subsystems</CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Operational readiness indicators.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            {/* PostgreSQL */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <Database className="w-4 h-4 text-blue-400" />
                <span className="text-slate-300 font-medium">PostgreSQL 18 DB</span>
              </div>
              <Badge
                variant={overview?.system_health?.database_status === "connected" ? "success" : "destructive"}
                className="text-[10px]"
              >
                {overview?.system_health?.database_status?.toUpperCase() || "CHECKING"}
              </Badge>
            </div>

            {/* Redis */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <Server className="w-4 h-4 text-purple-400" />
                <span className="text-slate-300 font-medium">Redis Rate Limiter</span>
              </div>
              <Badge
                variant={
                  overview?.system_health?.redis_status === "connected"
                    ? "success"
                    : overview?.system_health?.redis_status === "disabled"
                    ? "outline"
                    : "warning"
                }
                className="text-[10px]"
              >
                {overview?.system_health?.redis_status?.toUpperCase() || "UNKNOWN"}
              </Badge>
            </div>

            {/* ECAPA-TDNN */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span className="text-slate-300 font-medium">ECAPA-TDNN PyTorch</span>
              </div>
              <Badge
                variant={overview?.system_health?.model_loaded ? "cyber" : "outline"}
                className="text-[10px]"
              >
                {overview?.system_health?.model_loaded ? "LOADED (192D)" : "STANDBY (ON-DEMAND)"}
              </Badge>
            </div>

            {/* AES-256-GCM Vault */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <Lock className="w-4 h-4 text-amber-400" />
                <span className="text-slate-300 font-medium">AES-256-GCM Vault</span>
              </div>
              <Badge
                variant={overview?.system_health?.encryption_configured ? "success" : "destructive"}
                className="text-[10px]"
              >
                {overview?.system_health?.encryption_configured ? "SECURED" : "UNCONFIGURED"}
              </Badge>
            </div>

            <Link href="/admin/system-health" className="block pt-2">
              <Button variant="outline" size="sm" className="w-full text-xs gap-1.5 border-slate-700 bg-slate-900/60">
                <span>View Full Telemetry</span>
                <ArrowRight className="w-3 h-3" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Recent Governance Audit Stream */}
      <Card className="border-slate-800 bg-slate-900/80">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold text-white">System Audit Log Stream</CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Recent security actions, status changes, and biometric lifecycle events.
            </CardDescription>
          </div>
          <Link href="/admin/audit-logs">
            <Button variant="ghost" size="sm" className="text-xs text-blue-400 hover:text-blue-300 gap-1">
              <span>View All Logs</span>
              <ArrowRight className="w-3 h-3" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent className="space-y-3">
          {overview?.recent_audit_events && overview.recent_audit_events.length > 0 ? (
            overview.recent_audit_events.map((log) => (
              <div
                key={log.id}
                className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs"
              >
                <div className="flex items-center gap-3">
                  <FileText className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <div>
                    <p className="font-semibold text-white font-mono">{log.action}</p>
                    <p className="text-[11px] text-slate-400">
                      Resource: <span className="font-mono text-slate-300">{log.resource_type}:{log.resource_id}</span> • {formatDateTime(log.created_at)}
                    </p>
                  </div>
                </div>
                <Badge variant="outline" className="text-[10px] font-mono text-blue-300 border-blue-500/30">
                  {log.resource_type.toUpperCase()}
                </Badge>
              </div>
            ))
          ) : (
            <div className="p-6 text-center text-slate-500 text-xs">
              No recent audit records found.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
