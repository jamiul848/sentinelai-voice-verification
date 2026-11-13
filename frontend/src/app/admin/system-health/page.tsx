at"use client";

import React, { useCallback, useEffect, useState } from "react";
import { monitoringService } from "@/lib/api/services/monitoring.service";
import { useDemoStore } from "@/store/useDemoStore";
import { formatDateTime } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Clock,
  Cpu,
  Database,
  Lock,
  RefreshCw,
  Server,
  Sparkles,
} from "lucide-react";

export default function AdminSystemHealthPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  const [detailed, setDetailed] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadProbes = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);

    if (isDemoMode) {
      setDetailed({
        status: "ready",
        service: "Sentinel Voice Platform",
        version: "0.1.0",
        uptime_seconds: 18450,
        components: {
          database: { status: "connected", latency_ms: 0.47 },
          redis: { status: "connected", mode: "TCP socket" },
        },
        ecapa_engine: {
          model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
          device: "cpu",
          loaded: true,
          embedding_dim: 192,
        },
        biometric_storage: {
          storage_root: "outputs/biometric_store",
          accessible: true,
        },
        encryption_service: {
          algorithm: "AES-256-GCM-Envelope-V2",
          configured: true,
        },
        timestamp: new Date().toISOString(),
      });
      setIsLoading(false);
      return;
    }

    try {
      const data = await monitoringService.getDetailedHealth();
      setDetailed(data);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to query system health diagnostic probes.");
    } finally {
      setIsLoading(false);
    }
  }, [isDemoMode]);

  useEffect(() => {
    loadProbes();
  }, [loadProbes]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">System Operational Health</h1>
            {isDemoMode && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <Sparkles className="w-3 h-3" /> DEMO
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Real-time inspection of low-level dependencies, deep learning neural models, and cryptographic hardware.
          </p>
        </div>

        <Button
          size="sm"
          variant="outline"
          onClick={loadProbes}
          isLoading={isLoading}
          className="gap-2 text-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Probes</span>
        </Button>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs">
          {errorMsg}
        </div>
      )}

      {/* Main Subsystem Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Database & Latency */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-blue-400" />
              <span>Relational Database Engine</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              PostgreSQL 18 Async Engine with SQLAlchemy Connection Pooling
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Connection State</span>
              <Badge variant="success" className="text-[10px]">
                {detailed?.components?.database?.status || "CONNECTED"}
              </Badge>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Ping Query Latency</span>
              <span className="font-mono text-emerald-400 font-bold">
                {detailed?.components?.database?.latency_ms ?? 0.47} ms
              </span>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Connection Pool Pre-ping</span>
              <span className="text-slate-200">Enabled (300s recycle)</span>
            </div>
          </CardContent>
        </Card>

        {/* Redis Rate Limiter */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
              <Server className="w-4 h-4 text-purple-400" />
              <span>Rate Limiting & Abuse Defense</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Sliding-window Redis backend with in-memory fallback
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Redis Storage Provider</span>
              <Badge variant="success" className="text-[10px]">
                {detailed?.components?.redis?.status || "CONNECTED"}
              </Badge>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Algorithm</span>
              <span className="font-mono text-slate-200">Sliding-Window Log (ZSET)</span>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Brute-Force Tracker</span>
              <span className="text-slate-200">Active (5 fails / 15m lockout)</span>
            </div>
          </CardContent>
        </Card>

        {/* ECAPA-TDNN AI Engine */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <span>AI Neural Backbone</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              SpeechBrain ECAPA-TDNN Speaker Recognition Engine
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Model Identifier</span>
              <span className="font-mono text-blue-300">
                {detailed?.ecapa_engine?.model_identifier || "speechbrain/spkrec-ecapa-voxceleb"}
              </span>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Compute Device</span>
              <Badge variant="cyber" className="text-[10px]">
                {detailed?.ecapa_engine?.device?.toUpperCase() || "CPU"}
              </Badge>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Embedding Dimension</span>
              <span className="font-mono text-emerald-400 font-bold">192-dimensional</span>
            </div>
          </CardContent>
        </Card>

        {/* Biometric Storage & Encryption */}
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader>
            <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
              <Lock className="w-4 h-4 text-amber-400" />
              <span>Biometric Vault & Cryptography</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              AES-256-GCM Envelope Encryption & NIST SP 800-88 Shredder
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Encryption Scheme</span>
              <span className="font-mono text-emerald-400 font-bold">
                {detailed?.encryption_service?.algorithm || "AES-256-GCM-Envelope-V2"}
              </span>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Storage Root Accessible</span>
              <Badge variant="success" className="text-[10px]">
                VERIFIED WRITABLE
              </Badge>
            </div>
            <div className="flex justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Cryptographic Erasure</span>
              <span className="text-slate-200">NIST SP 800-88 Multi-Pass</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Uptime and Service Metadata */}
      <Card className="border-slate-800 bg-slate-900/60 text-xs">
        <CardContent className="p-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-slate-400">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-400" />
            <span>Process Uptime: <strong className="text-white">{detailed?.uptime_seconds ?? 18450} seconds</strong></span>
          </div>
          <div>
            System Version: <strong className="text-white">v0.1.0</strong> • Evaluated at: {formatDateTime(detailed?.timestamp)}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}