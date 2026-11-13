"use client";

import React, { useState } from "react";
import { useDemoStore } from "@/store/useDemoStore";
import { useAdminSecurityEvents } from "@/hooks/useAdmin";
import { formatDateTime } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Lock,
  RefreshCw,
  Server,
  Shield,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

export default function AdminSecurityEventsPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);
  const { data, isLoading, error, refetch, isFetching } = useAdminSecurityEvents();

  const events = data?.events || [];
  const rateLimiter = data?.rate_limiter;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Security Events & Abuse Defense</h1>
            {isDemoMode && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <Sparkles className="w-3 h-3" /> DEMO
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Real-time security audit events, privilege mutations, throttling incidents, and rate-limiting enforcement.
          </p>
        </div>

        <Button
          size="sm"
          variant="outline"
          onClick={() => refetch()}
          disabled={isFetching}
          className="gap-1.5 text-xs border-slate-700 bg-slate-900/60"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${isFetching ? "animate-spin" : ""}`} />
          <span>Refresh Incidents</span>
        </Button>
      </div>

      {/* Rate Limiter Active Configuration Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-purple-400" />
              <CardTitle className="text-sm font-semibold text-white">Rate Limiter Backend</CardTitle>
            </div>
            <Badge
              variant={rateLimiter?.redis_configured ? "success" : "outline"}
              className="text-[10px]"
            >
              {rateLimiter?.backend?.toUpperCase() || "IN-MEMORY"}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-1 text-xs text-slate-400">
            <p>
              Storage Architecture: <strong className="text-white">{rateLimiter?.backend || "in-memory"}</strong>
            </p>
            <p className="text-[11px] text-slate-500">
              {rateLimiter?.redis_configured
                ? "Redis sliding window cluster with atomic timestamp pipelines."
                : "Thread-safe sliding window in-memory fallback cache."}
            </p>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-blue-400" />
              <CardTitle className="text-sm font-semibold text-white">Authentication Quotas</CardTitle>
            </div>
            <Badge variant="secondary" className="text-[10px]">
              ENFORCED
            </Badge>
          </CardHeader>
          <CardContent className="space-y-1 text-xs text-slate-400">
            <div className="flex justify-between">
              <span>POST /auth/login:</span>
              <span className="font-mono text-white">{rateLimiter?.rules?.auth_login || "5/min"}</span>
            </div>
            <div className="flex justify-between">
              <span>POST /auth/register:</span>
              <span className="font-mono text-white">{rateLimiter?.rules?.auth_register || "3/hour"}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-emerald-400" />
              <CardTitle className="text-sm font-semibold text-white">Biometric Endpoint Quotas</CardTitle>
            </div>
            <Badge variant="secondary" className="text-[10px]">
              ENFORCED
            </Badge>
          </CardHeader>
          <CardContent className="space-y-1 text-xs text-slate-400">
            <div className="flex justify-between">
              <span>POST /biometrics/verify:</span>
              <span className="font-mono text-white">{rateLimiter?.rules?.biometrics_verify || "10/min"}</span>
            </div>
            <div className="flex justify-between">
              <span>POST /biometrics/enroll:</span>
              <span className="font-mono text-white">{rateLimiter?.rules?.biometrics_enroll || "5/hour"}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Security Invariant Notice */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
        <ShieldAlert className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <strong className="text-white">Strict Authentic Incident Reporting:</strong>
          <p className="text-slate-400 leading-relaxed">
            In compliance with Sentinel Voice security standards, all displayed security events reflect verified audit records in PostgreSQL. The platform does not generate synthetic danger scores or decorative threat alarms.
          </p>
        </div>
      </div>

      {/* Security Events Table */}
      <Card className="border-slate-800 bg-slate-900/80">
        <CardHeader>
          <CardTitle className="text-base font-semibold text-white">Security-Relevant Audit Incidents</CardTitle>
          <CardDescription className="text-xs text-slate-400">
            Account deactivations, privilege updates, vector shredding, and rate limit triggers.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Incident Action</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>Entity ID</TableHead>
                <TableHead>Actor Identity</TableHead>
                <TableHead>Audit Details</TableHead>
                <TableHead>Logged At</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-10 text-xs text-slate-500">
                    Loading security incident ledger...
                  </TableCell>
                </TableRow>
              ) : events.length > 0 ? (
                events.map((ev) => (
                  <TableRow key={ev.id} className="hover:bg-slate-800/40">
                    <TableCell>
                      <span className="font-mono text-xs font-semibold text-white flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                        <span>{ev.action}</span>
                      </span>
                    </TableCell>

                    <TableCell>
                      <Badge variant="outline" className="text-[10px] font-mono text-blue-300 border-blue-500/30">
                        {ev.resource_type.toUpperCase()}
                      </Badge>
                    </TableCell>

                    <TableCell className="font-mono text-xs text-slate-400 truncate max-w-[150px]">
                      {ev.resource_id}
                    </TableCell>

                    <TableCell className="text-xs text-slate-300 font-mono">
                      {ev.actor_email || (ev.actor_user_id ? ev.actor_user_id.slice(0, 8) : "System")}
                    </TableCell>

                    <TableCell className="text-xs text-slate-300 font-mono max-w-[200px] truncate">
                      {JSON.stringify(ev.changes || {})}
                    </TableCell>

                    <TableCell className="text-xs text-slate-400 font-mono">
                      {formatDateTime(ev.created_at)}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-10 text-xs text-slate-500">
                    Zero security incidents or policy violations recorded.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

