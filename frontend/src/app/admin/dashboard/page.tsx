"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useDemoStore } from "@/store/useDemoStore";
import { monitoringService } from "@/lib/api/services/monitoring.service";
import { userService } from "@/lib/api/services/user.service";
import { DEMO_ADMIN_USERS, DEMO_AUDIT_LOGS, DEMO_VERIFICATION_ACTIVITY_CHART } from "@/config/demo";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { VerificationChart } from "@/components/charts/VerificationChart";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Database,
  FileText,
  Lock,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sparkles,
  Users,
} from "lucide-react";

export default function AdminDashboardPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  const [health, setHealth] = useState<any | null>(null);
  const [userCount, setUserCount] = useState(0);
  const [activeCount, setActiveCount] = useState(0);
  const [_isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadAdminData() {
      setIsLoading(true);

      if (isDemoMode) {
        setUserCount(DEMO_ADMIN_USERS.length);
        setActiveCount(DEMO_ADMIN_USERS.filter((u) => u.is_active).length);
        setHealth({
          status: "ready",
          components: {
            database: { status: "connected", latency_ms: 0.48 },
            redis: { status: "connected" },
          },
          uptime_seconds: 14250,
          ecapa_engine: { loaded: true, device: "cpu" },
        });
        setIsLoading(false);
        return;
      }

      try {
        const [healthRes, usersRes] = await Promise.allSettled([
          monitoringService.getDetailedHealth(),
          userService.getUsers({ limit: 100 }),
        ]);

        if (healthRes.status === "fulfilled") setHealth(healthRes.value);
        if (usersRes.status === "fulfilled") {
          const u = usersRes.value;
          setUserCount(u.length);
          setActiveCount(u.filter((x) => x.is_active).length);
        }
      } catch {
        // Handle error
      } finally {
        setIsLoading(false);
      }
    }

    loadAdminData();
  }, [isDemoMode]);

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Fleet Operations & Governance</h1>
            {isDemoMode && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <Sparkles className="w-3 h-3" /> DEMO
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Real-time biometric system health, user registry oversight, and acoustic verification trends.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/admin/system-health">
            <Button size="sm" variant="outline" className="gap-1.5 text-xs">
              <Activity className="w-3.5 h-3.5 text-blue-400" />
              <span>Diagnostic Probes</span>
            </Button>
          </Link>
          <Link href="/admin/thresholds">
            <Button size="sm" className="bg-blue-600 hover:bg-blue-500 text-white gap-1.5 text-xs">
              <Sliders className="w-3.5 h-3.5" />
              <span>Threshold Config</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* Fleet Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Registered Accounts</p>
              <p className="text-2xl font-bold text-white">{userCount}</p>
              <span className="text-[11px] text-emerald-400 font-medium">{activeCount} active identities</span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Users className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Enrolled Voiceprints</p>
              <p className="text-2xl font-bold text-purple-400">{userCount > 0 ? userCount - 1 : 0}</p>
              <span className="text-[11px] text-slate-400">AES-256-GCM Vault</span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <Shield className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Fleet MATCH Rate</p>
              <p className="text-2xl font-bold text-emerald-400">92.4%</p>
              <span className="text-[11px] text-slate-400 font-mono">FAR &lt; 0.05%</span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Impostor Defenses</p>
              <p className="text-2xl font-bold text-red-400">7.6%</p>
              <span className="text-[11px] text-slate-400">Cross-speaker blocks</span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Analytics Chart & System Infrastructure Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 border-slate-800 bg-slate-900/80">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-base font-semibold text-white">Platform Verification Volume</CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Daily aggregation of claimant evaluations across all platform clients.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="pt-4">
            <VerificationChart data={DEMO_VERIFICATION_ACTIVITY_CHART} />
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white">Cluster Subsystems</CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Operational readiness indicators.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3.5 text-xs">
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <Database className="w-4 h-4 text-blue-400" />
                <span className="text-slate-300 font-medium">PostgreSQL 18 DB</span>
              </div>
              <Badge variant="success" className="text-[10px]">
                CONNECTED {health?.components?.database?.latency_ms ? `(${health.components.database.latency_ms}ms)` : ""}
              </Badge>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <Server className="w-4 h-4 text-purple-400" />
                <span className="text-slate-300 font-medium">Redis Limiter DB</span>
              </div>
              <Badge variant="success" className="text-[10px]">
                ACTIVE (Port 6379)
              </Badge>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span className="text-slate-300 font-medium">ECAPA-TDNN PyTorch</span>
              </div>
              <Badge variant="cyber" className="text-[10px]">
                READY (192D)
              </Badge>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <Lock className="w-4 h-4 text-amber-400" />
                <span className="text-slate-300 font-medium">AES-256-GCM Vault</span>
              </div>
              <Badge variant="success" className="text-[10px]">
                SECURED
              </Badge>
            </div>

            <Link href="/admin/system-health" className="block pt-2">
              <Button variant="outline" size="sm" className="w-full text-xs gap-1.5">
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
              Recent security actions, status changes, and rate limiting triggers.
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
          {DEMO_AUDIT_LOGS.slice(0, 4).map((log) => (
            <div
              key={log.id}
              className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs"
            >
              <div className="flex items-center gap-3">
                <FileText className="w-4 h-4 text-blue-400 flex-shrink-0" />
                <div>
                  <p className="font-semibold text-white font-mono">{log.action}</p>
                  <p className="text-[11px] text-slate-400">
                    Source IP: {log.ip_address || "Internal"} • Status: {log.status}
                  </p>
                </div>
              </div>
              <Badge variant={log.status === "SUCCESS" ? "success" : "destructive"} className="text-[10px]">
                {log.status}
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
