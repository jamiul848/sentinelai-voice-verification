"use client";

import React, { useState } from "react";
import { useDemoStore } from "@/store/useDemoStore";
import { useAdminAuditLogs } from "@/hooks/useAdmin";
import { AdminAuditLogItem } from "@/types";
import { formatDateTime } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  CheckCircle2,
  FileCode,
  FileText,
  Lock,
  RefreshCw,
  Search,
  Shield,
  Sparkles,
} from "lucide-react";

export default function AdminAuditLogsPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  const [searchTerm, setSearchTerm] = useState("");
  const [actionCategory, setActionCategory] = useState<"ALL" | "USER" | "PROFILE" | "CONSENT" | "THRESHOLD">("ALL");

  const { data, isLoading, error, refetch, isFetching } = useAdminAuditLogs({ limit: 100 });
  const logs = data?.items || [];

  // Selected log for detail drawer
  const [selectedLog, setSelectedLog] = useState<AdminAuditLogItem | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const filteredLogs = logs.filter((log) => {
    const term = searchTerm.toLowerCase();
    const matchesSearch =
      log.action.toLowerCase().includes(term) ||
      log.resource_type.toLowerCase().includes(term) ||
      log.resource_id.toLowerCase().includes(term) ||
      (log.actor_email && log.actor_email.toLowerCase().includes(term)) ||
      (log.actor_user_id && log.actor_user_id.toLowerCase().includes(term));

    const matchesCategory =
      actionCategory === "ALL" ||
      (actionCategory === "USER" && log.resource_type === "user") ||
      (actionCategory === "PROFILE" && log.resource_type === "voice_profile") ||
      (actionCategory === "CONSENT" && log.resource_type === "consent") ||
      (actionCategory === "THRESHOLD" && log.resource_type === "threshold_configuration");

    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Global Security Audit Trail</h1>
            {isDemoMode && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <Sparkles className="w-3 h-3" /> DEMO
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Append-only immutable record of authentication, biometric lifecycles, and administrative actions.
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
          <span>Refresh Trail</span>
        </Button>
      </div>

      {/* Audit Invariant Banner */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
        <Lock className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <strong className="text-white">Tamper-Proof Audit Integrity:</strong>
          <p className="text-slate-400 leading-relaxed">
            Audit logs are written synchronously during state mutations in PostgreSQL table <code className="font-mono text-blue-300">audit_logs</code>. Audit records are strictly read-only from the frontend without edit or delete mechanisms.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <Input
            placeholder="Search by action, resource ID, or actor..."
            className="pl-9 text-xs h-9 bg-slate-950/80 border-slate-700"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
          <button
            onClick={() => setActionCategory("ALL")}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              actionCategory === "ALL" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            All Logs ({data?.total ?? 0})
          </button>
          <button
            onClick={() => setActionCategory("USER")}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              actionCategory === "USER" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            User
          </button>
          <button
            onClick={() => setActionCategory("PROFILE")}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              actionCategory === "PROFILE" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            Voiceprint
          </button>
          <button
            onClick={() => setActionCategory("CONSENT")}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              actionCategory === "CONSENT" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            Consent
          </button>
          <button
            onClick={() => setActionCategory("THRESHOLD")}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              actionCategory === "THRESHOLD" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            Threshold
          </button>
        </div>
      </div>

      {/* Audit Log Table */}
      <Card className="border-slate-800 bg-slate-900/80">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Event Action</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>Target Entity ID</TableHead>
                <TableHead>Actor Identity</TableHead>
                <TableHead>Timestamp</TableHead>
                <TableHead className="text-right">Payload</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-10 text-xs text-slate-500">
                    Loading security audit trail...
                  </TableCell>
                </TableRow>
              ) : filteredLogs.length > 0 ? (
                filteredLogs.map((log) => (
                  <TableRow key={log.id} className="hover:bg-slate-800/40">
                    <TableCell>
                      <span className="font-mono text-xs font-semibold text-white">
                        {log.action}
                      </span>
                    </TableCell>

                    <TableCell>
                      <Badge variant="outline" className="text-[10px] font-mono text-blue-300 border-blue-500/30">
                        {log.resource_type.toUpperCase()}
                      </Badge>
                    </TableCell>

                    <TableCell className="font-mono text-xs text-slate-400 truncate max-w-[160px]">
                      {log.resource_id}
                    </TableCell>

                    <TableCell>
                      <span className="text-xs text-slate-300 font-mono">
                        {log.actor_email || (log.actor_user_id ? log.actor_user_id.slice(0, 8) : "System")}
                      </span>
                    </TableCell>

                    <TableCell className="text-xs text-slate-400 font-mono">
                      {formatDateTime(log.created_at)}
                    </TableCell>

                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setSelectedLog(log);
                          setIsDetailOpen(true);
                        }}
                        className="text-xs h-7 px-2 text-slate-300 hover:text-white"
                      >
                        Inspect
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-10 text-xs text-slate-500">
                    No matching audit logs discovered.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Audit Detail Dialog */}
      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="max-w-lg bg-slate-900 border-slate-800 text-slate-100">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <FileCode className="w-5 h-5 text-blue-400" />
              <span>Audit Log Record Inspector</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-400">
              Sanitized immutable change event {selectedLog?.id}.
            </DialogDescription>
          </DialogHeader>

          {selectedLog && (
            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-400">Action</span>
                  <p className="font-mono text-white text-xs font-semibold">{selectedLog.action}</p>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-400">Resource</span>
                  <p className="font-mono text-blue-300 text-xs">{selectedLog.resource_type}</p>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-400">Entity Identifier</span>
                  <p className="font-mono text-white text-[11px] truncate">{selectedLog.resource_id}</p>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-400">Timestamp</span>
                  <p className="font-mono text-slate-300 text-[11px]">{formatDateTime(selectedLog.created_at)}</p>
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-slate-400">Sanitized Changes Payload:</span>
                <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto max-h-48">
                  {JSON.stringify(selectedLog.changes || {}, null, 2)}
                </pre>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsDetailOpen(false)}
              className="text-xs"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
