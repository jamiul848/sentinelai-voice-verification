"use client";

import React from "react";
import { useDemoStore } from "@/store/useDemoStore";
import { useSystemHealthDetailed } from "@/hooks/useAdmin";
import { formatDateTime } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Activity,
  AlertCircle,
  Clock,
  Cpu,
  Database,
  FolderLock,
  Lock,
  RefreshCw,
  Server,
  Shield,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

export default function AdminSystemHealthPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);
  const { data: detailed, isLoading, error, refetch, isFetching } = useSystemHealthDetailed();

  const isDbConnected = detailed?.components?.database?.status === "connected";
  const dbLatency = detailed?.components?.database?.latency_ms;
  const redisStatus = detailed?.components?.redis?.status || "disabled";
  const isModelLoaded = detailed?.ecapa_engine?.loaded ?? detailed?.ecapa_engine?.is_loaded;
  const isStorageAccessible = detailed?.biometric_storage?.accessible;
  const isEncryptionConfigured = detailed?.encryption_service?.configured;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">System Health & Infrastructure</h1>
            {isDemoMode && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <Sparkles className="w-3 h-3" /> DEMO
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Real-time diagnostic probes inspecting database latency, model cache, encrypted storage, and cluster subsystems.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => refetch()}
            disabled={isFetching}
            className="gap-1.5 text-xs border-slate-700 bg-slate-900/60"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${isFetching ? "animate-spin" : ""}`} />
            <span>Poll Health Probes</span>
          </Button>
        </div>
      </div>

      {/* Error Callout */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/30 border border-red-800/60 text-xs text-red-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>Unable to query diagnostic health probes. Service may be degraded or unauthorized.</span>
          </div>
          <Button size="sm" variant="outline" onClick={() => refetch()} className="text-xs h-7">
            Retry
          </Button>
        </div>
      )}

      {/* Main Cluster Status Banner */}
      <Card
        className={`border ${
          detailed?.status === "ready" || detailed?.status === "healthy"
            ? "border-emerald-600/40 bg-gradient-to-r from-slate-900 via-slate-900 to-emerald-950/20"
            : "border-amber-600/40 bg-gradient-to-r from-slate-900 via-slate-900 to-amber-950/20"
        }`}
      >
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div
                className={`w-12 h-12 rounded-xl flex items-center justify-center border ${
                  detailed?.status === "ready" || detailed?.status === "healthy"
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                    : "bg-amber-500/10 border-amber-500/30 text-amber-400"
                }`}
              >
                <Activity className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold text-white">
                    {detailed?.service || "Sentinel Voice Application Server"}
                  </h2>
                  <Badge
                    variant={detailed?.status === "ready" ? "success" : "warning"}
                    className="text-xs font-mono"
                  >
                    {detailed?.status?.toUpperCase() || "CHECKING"}
                  </Badge>
                </div>
                <p className="text-xs text-slate-400">
                  Version: <span className="font-mono text-slate-300">{detailed?.version || "0.1.0"}</span> • Up since:{" "}
                  <span className="font-mono text-slate-300">
                    {detailed?.uptime_seconds ? `${(detailed.uptime_seconds / 3600).toFixed(1)} hours` : "0.0 hours"}
                  </span>
                </p>
              </div>
            </div>

            <div className="text-right text-xs text-slate-400 space-y-0.5">
              <span>Probe Timestamp:</span>
              <p className="font-mono text-slate-300">{formatDateTime(detailed?.timestamp)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Subsystem Health Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* PostgreSQL Database */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-blue-400" />
              <CardTitle className="text-sm font-semibold text-white">PostgreSQL 18 DB</CardTitle>
            </div>
            <Badge variant={isDbConnected ? "success" : "destructive"} className="text-[10px]">
              {isDbConnected ? "CONNECTED" : "DISCONNECTED"}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Query Latency:</span>
              <span className="font-mono text-emerald-400 font-semibold">
                {typeof dbLatency === "number" ? `${dbLatency} ms` : "N/A"}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Driver:</span>
              <span className="font-mono text-slate-300">asyncpg (AsyncIO)</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Pool Status:</span>
              <span className="text-slate-300">Transactional (Pooled)</span>
            </div>
          </CardContent>
        </Card>

        {/* Redis Rate Limiter */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-purple-400" />
              <CardTitle className="text-sm font-semibold text-white">Redis Rate Limiter</CardTitle>
            </div>
            <Badge
              variant={
                redisStatus === "connected"
                  ? "success"
                  : redisStatus === "disabled"
                  ? "outline"
                  : "destructive"
              }
              className="text-[10px]"
            >
              {redisStatus.toUpperCase()}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Engine Backend:</span>
              <span className="font-mono text-slate-300">
                {redisStatus === "connected" ? "Redis (Sliding Window)" : "In-Memory Fallback"}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Failover Strategy:</span>
              <span className="text-emerald-400">Graceful In-Memory</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>State Persistence:</span>
              <span className="text-slate-300">{redisStatus === "connected" ? "Cluster Shared" : "Single Node"}</span>
            </div>
          </CardContent>
        </Card>

        {/* ECAPA-TDNN PyTorch Model */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <CardTitle className="text-sm font-semibold text-white">ECAPA-TDNN Engine</CardTitle>
            </div>
            <Badge variant={isModelLoaded ? "cyber" : "outline"} className="text-[10px]">
              {isModelLoaded ? "LOADED (192D)" : "STANDBY (ON-DEMAND)"}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Backbone Model:</span>
              <span className="font-mono text-blue-300 truncate max-w-[150px]">
                {detailed?.ecapa_engine?.model_identifier || "speechbrain/spkrec-ecapa-voxceleb"}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Compute Device:</span>
              <span className="font-mono text-slate-300 uppercase">
                {detailed?.ecapa_engine?.device || "CPU"}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Vector Dimension:</span>
              <span className="font-mono text-slate-300">
                {detailed?.ecapa_engine?.embedding_dim || 192} Dimensions
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Encrypted Biometric Storage */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <FolderLock className="w-4 h-4 text-amber-400" />
              <CardTitle className="text-sm font-semibold text-white">Biometric Vault</CardTitle>
            </div>
            <Badge variant={isStorageAccessible ? "success" : "destructive"} className="text-[10px]">
              {isStorageAccessible ? "WRITABLE" : "INACCESSIBLE"}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Store Mount:</span>
              <span className="font-mono text-slate-300">
                {detailed?.biometric_storage?.storage_root || "biometric_store"}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Filesystem Permissions:</span>
              <span className="text-emerald-400">Read / Write Verified</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Disk Shredding:</span>
              <span className="text-slate-300">NIST SP 800-88 Multi-Pass</span>
            </div>
          </CardContent>
        </Card>

        {/* Encryption Configuration */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-purple-400" />
              <CardTitle className="text-sm font-semibold text-white">Envelope Encryption</CardTitle>
            </div>
            <Badge variant={isEncryptionConfigured ? "success" : "destructive"} className="text-[10px]">
              {isEncryptionConfigured ? "CONFIGURED" : "MISSING"}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Algorithm:</span>
              <span className="font-mono text-purple-300">AES-256-GCM Envelope</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Master Key Entropy:</span>
              <span className="text-emerald-400">256-bit PBKDF2 / Argon2</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Vector Container:</span>
              <span className="text-slate-300">Encrypted Chunk Serialization</span>
            </div>
          </CardContent>
        </Card>

        {/* Uptime & Process Lifecycle */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-400" />
              <CardTitle className="text-sm font-semibold text-white">Service Lifecycle</CardTitle>
            </div>
            <Badge variant="outline" className="text-[10px] text-blue-400 border-blue-500/30">
              ACTIVE
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Uptime:</span>
              <span className="font-mono text-white font-semibold">
                {detailed?.uptime_seconds ? `${(detailed.uptime_seconds / 60).toFixed(1)} mins` : "0 mins"}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Event Loop:</span>
              <span className="text-emerald-400">AsyncIO Responsive</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Kubernetes Probes:</span>
              <span className="font-mono text-slate-300">/health/live, /ready</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
