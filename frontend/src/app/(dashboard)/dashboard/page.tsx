"use client";

import React, { useMemo } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/store/useAuthStore";
import { useDemoStore } from "@/store/useDemoStore";
import { biometricsService } from "@/lib/api/services/biometrics.service";
import {
  DEMO_PROFILE,
  DEMO_VERIFICATION_ACTIVITY_CHART,
  DEMO_VERIFICATION_HISTORY,
} from "@/config/demo";
import { VerificationHistoryItem, VoiceProfile } from "@/types";
import { formatDateTime, formatLatency, formatScore, truncateId } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { VerificationChart } from "@/components/charts/VerificationChart";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  History,
  Lock,
  Mic,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  XCircle,
} from "lucide-react";

export default function UserDashboardPage() {
  const user = useAuthStore((s) => s.user);
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  // TanStack Query for Biometric Profile
  const {
    data: profileData,
    isLoading: isProfileLoading,
    error: profileError,
  } = useQuery<VoiceProfile | null>({
    queryKey: ["biometrics", "profile", isDemoMode],
    queryFn: async () => {
      if (isDemoMode) return DEMO_PROFILE;
      return await biometricsService.getProfile();
    },
    staleTime: 60 * 1000,
  });

  // TanStack Query for Verification History
  const {
    data: historyData,
    isLoading: isHistoryLoading,
    error: historyError,
  } = useQuery<{ items: VerificationHistoryItem[]; total: number }>({
    queryKey: ["biometrics", "history", isDemoMode],
    queryFn: async () => {
      if (isDemoMode) {
        return {
          items: DEMO_VERIFICATION_HISTORY,
          total: DEMO_VERIFICATION_HISTORY.length,
        };
      }
      const res = await biometricsService.getVerificationHistory({ limit: 50 });
      return {
        items: res?.items || [],
        total: res?.total || 0,
      };
    },
    staleTime: 30 * 1000,
  });

  const profile = profileData || null;
  const history = useMemo(() => historyData?.items || [], [historyData?.items]);
  const totalVerifications = historyData?.total ?? history.length;
  const matches = history.filter((h) => h.decision === "MATCH").length;
  const nonMatches = history.filter((h) => h.decision === "NO_MATCH").length;

  // Derive chronological activity timeline for Recharts visualization
  const chartData = useMemo(() => {
    if (isDemoMode) {
      return DEMO_VERIFICATION_ACTIVITY_CHART;
    }

    if (history.length === 0) {
      return [{ date: "No Activity", matches: 0, nonMatches: 0 }];
    }

    // Group items by calendar date
    const dateMap = new Map<string, { matches: number; nonMatches: number }>();
    // Iterate chronological order (reverse of newest-first history)
    const reversedHistory = [...history].reverse();

    for (const item of reversedHistory) {
      const dateKey = item.created_at ? item.created_at.split("T")[0] : "Recent";
      const current = dateMap.get(dateKey) || { matches: 0, nonMatches: 0 };
      if (item.decision === "MATCH") {
        current.matches += 1;
      } else {
        current.nonMatches += 1;
      }
      dateMap.set(dateKey, current);
    }

    return Array.from(dateMap.entries()).map(([date, counts]) => ({
      date,
      matches: counts.matches,
      nonMatches: counts.nonMatches,
    }));
  }, [isDemoMode, history]);

  const fetchError = profileError?.message || historyError?.message;
  const isLoading = isProfileLoading || isHistoryLoading;

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-blue-950/60 via-slate-900 to-slate-900 border border-blue-900/40 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Welcome back, {user?.full_name || "Operator"}
            </h1>
            {isDemoMode && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <Sparkles className="w-3 h-3" /> DEMO
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Acoustic speaker verification gateway and live biometric profile status.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link href="/verification">
            <Button className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs shadow-sm">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Verify Voice</span>
            </Button>
          </Link>
          <Link href="/enrollment">
            <Button variant="secondary" className="gap-2 text-xs">
              <Mic className="w-3.5 h-3.5 text-blue-400" />
              <span>Enroll Voice</span>
            </Button>
          </Link>
        </div>
      </div>

      {fetchError && !isDemoMode && (
        <div className="p-4 rounded-xl bg-red-950/50 border border-red-800 text-red-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 flex-shrink-0" />
            <span>{fetchError}</span>
          </div>
          <Button size="sm" variant="outline" onClick={() => window.location.reload()} className="text-xs">
            Retry
          </Button>
        </div>
      )}

      {/* Metric Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Profile Status Card */}
        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Voiceprint State</p>
              <div className="pt-0.5">
                {isLoading ? (
                  <span className="text-xs text-slate-500 animate-pulse">Loading...</span>
                ) : profile?.status === "ACTIVE" ? (
                  <Badge variant="success" className="gap-1 text-xs">
                    <ShieldCheck className="w-3.5 h-3.5" /> ACTIVE
                  </Badge>
                ) : profile?.status === "REVOKED" ? (
                  <Badge variant="destructive" className="gap-1 text-xs">
                    <XCircle className="w-3.5 h-3.5" /> REVOKED
                  </Badge>
                ) : (
                  <Badge variant="outline" className="gap-1 text-xs text-amber-400 border-amber-500/30">
                    NOT ENROLLED
                  </Badge>
                )}
              </div>
            </div>
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Shield className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        {/* Total Verifications Card */}
        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Total Evaluations</p>
              <p className="text-2xl font-bold text-white">
                {isLoading ? "..." : totalVerifications}
              </p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <History className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        {/* Genuine Matches Card */}
        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Authentic MATCH</p>
              <p className="text-2xl font-bold text-emerald-400">
                {isLoading ? "..." : matches}
              </p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        {/* Impostor Rejections Card */}
        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-400">Impostor Repelled</p>
              <p className="text-2xl font-bold text-red-400">
                {isLoading ? "..." : nonMatches}
              </p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Analytics Chart & Profile Summary Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Verification Trends Chart */}
        <Card className="lg:col-span-2 border-slate-800 bg-slate-900/80">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-base font-semibold text-white">Verification Activity Stream</CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Temporal distribution of genuine authentications versus impostor rejections.
              </CardDescription>
            </div>
            {isDemoMode && (
              <Badge variant="outline" className="text-[10px] text-amber-400 border-amber-500/30">
                Sample Projection
              </Badge>
            )}
          </CardHeader>
          <CardContent className="pt-4">
            <VerificationChart data={chartData} />
          </CardContent>
        </Card>

        {/* Active Profile Telemetry */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white">Biometric Vault</CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Cryptographic template metadata.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3.5 text-xs">
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Profile UUID</span>
                <span className="font-mono text-slate-200">
                  {profile ? truncateId(profile.id) : "None"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Enrolled Samples</span>
                <span className="text-slate-200 font-semibold">{profile?.sample_count ?? 0} recordings</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Intra-Session Consistency</span>
                <span className="font-mono text-emerald-400">
                  {profile?.mean_pairwise_similarity
                    ? formatScore(profile.mean_pairwise_similarity)
                    : "N/A"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Model Backbone</span>
                <span className="font-mono text-blue-300">ECAPA-TDNN (192D)</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
              <div className="flex items-center gap-1.5 text-slate-300 font-medium">
                <Lock className="w-3.5 h-3.5 text-blue-400" />
                <span>Encryption Envelope</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Protected via AES-256-GCM envelope encryption with per-profile DEKs. NIST SP 800-88 erasure supported upon revocation.
              </p>
            </div>

            <Link href="/profile" className="block pt-1">
              <Button variant="outline" size="sm" className="w-full text-xs gap-1.5">
                <span>Manage Profile</span>
                <ArrowRight className="w-3 h-3" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity Table */}
      <Card className="border-slate-800 bg-slate-900/80">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold text-white">Recent Verification Trials</CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Audit log of 1:1 acoustic identity assessments.
            </CardDescription>
          </div>
          <Link href="/history">
            <Button variant="ghost" size="sm" className="text-xs text-blue-400 hover:text-blue-300 gap-1">
              <span>View Full History</span>
              <ArrowRight className="w-3 h-3" />
            </Button>
          </Link>
        </CardHeader>

        <CardContent className="p-0">
          {history.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">
              No recent verification trials recorded. Submit a voice probe to evaluate your voiceprint.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Event ID</TableHead>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Similarity</TableHead>
                  <TableHead>Threshold</TableHead>
                  <TableHead>Latency</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.slice(0, 5).map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono text-xs text-slate-300">{truncateId(item.id)}</TableCell>
                    <TableCell className="text-xs text-slate-400">{formatDateTime(item.created_at)}</TableCell>
                    <TableCell>
                      {item.decision === "MATCH" ? (
                        <Badge variant="success" className="text-[11px] gap-1">
                          <CheckCircle2 className="w-3 h-3" /> MATCH
                        </Badge>
                      ) : (
                        <Badge variant="destructive" className="text-[11px] gap-1">
                          <XCircle className="w-3 h-3" /> NO_MATCH
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-200">
                      {formatScore(item.similarity_score)}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-400">
                      {formatScore(item.applied_threshold)}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400">
                      <span className="flex items-center gap-1 font-mono">
                        <Clock className="w-3 h-3 text-slate-500" />
                        {formatLatency(item.processing_time_ms)}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
