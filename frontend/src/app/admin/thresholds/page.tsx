"use client";

import React from "react";
import { useDemoStore } from "@/store/useDemoStore";
import { DEMO_THRESHOLDS } from "@/config/demo";
import { formatDateTime, formatScore } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CheckCircle2, Info, Sparkles } from "lucide-react";

export default function AdminThresholdsPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-white tracking-tight">Threshold Configurations</h1>
          {isDemoMode && (
            <Badge variant="warning" className="gap-1 text-[10px]">
              <Sparkles className="w-3 h-3" /> DEMO
            </Badge>
          )}
        </div>
        <p className="text-xs sm:text-sm text-slate-400">
          Calibrated decision boundaries loaded dynamically from PostgreSQL by the speaker verification engine.
        </p>
      </div>

      {/* Governance Banner */}
      <div className="p-4 rounded-xl bg-blue-950/40 border border-blue-800/60 text-xs text-blue-200 flex items-start gap-3">
        <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <strong className="text-white">Dynamic Threshold Calibration Architecture:</strong>
          <p className="text-slate-300 leading-relaxed">
            Threshold records are versioned and tied directly to the neural model identifier (`speechbrain/spkrec-ecapa-voxceleb`). The verification engine retrieves the active operational threshold at query time, enabling real-time security adjustments without recompiling or redeploying the backend.
          </p>
        </div>
      </div>

      {/* Threshold List */}
      <Card className="border-slate-800 bg-slate-900/80">
        <CardHeader>
          <CardTitle className="text-base font-semibold text-white">Registered Operational Thresholds</CardTitle>
          <CardDescription className="text-xs text-slate-400">
            Database table: <code className="font-mono text-blue-300">threshold_configurations</code>
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Version Tag</TableHead>
                <TableHead>Model Backbone</TableHead>
                <TableHead>Threshold (Cosine)</TableHead>
                <TableHead>Empirical EER</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Calibration Notes</TableHead>
                <TableHead>Committed</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {DEMO_THRESHOLDS.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-mono text-xs font-semibold text-white">
                    {item.version_tag}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-slate-400">
                    {item.model_identifier}
                  </TableCell>
                  <TableCell className="font-mono text-xs font-bold text-emerald-400">
                    {formatScore(item.calibrated_threshold, 6)}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-slate-300">
                    {item.eer_percent.toFixed(2)}%
                  </TableCell>
                  <TableCell>
                    {item.is_active ? (
                      <Badge variant="success" className="text-[10px] gap-1">
                        <CheckCircle2 className="w-3 h-3" /> ACTIVE
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px] text-slate-500">
                        ARCHIVED
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-xs text-slate-400 max-w-xs truncate">
                    {item.description}
                  </TableCell>
                  <TableCell className="text-xs text-slate-500">
                    {formatDateTime(item.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
