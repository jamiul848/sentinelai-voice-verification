"use client";

import React, { useState } from "react";
import { useDemoStore } from "@/store/useDemoStore";
import { DEMO_AUDIT_LOGS } from "@/config/demo";
import { formatDateTime, truncateId } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Search, Sparkles } from "lucide-react";

export default function AdminAuditLogsPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);
  const [searchTerm, setSearchTerm] = useState("");

  const filteredLogs = DEMO_AUDIT_LOGS.filter((log) => {
    const q = searchTerm.toLowerCase();
    return (
      log.action.toLowerCase().includes(q) ||
      (log.ip_address && log.ip_address.includes(q)) ||
      log.status.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-white tracking-tight">Security Audit Logs</h1>
          {isDemoMode && (
            <Badge variant="warning" className="gap-1 text-[10px]">
              <Sparkles className="w-3 h-3" /> DEMO
            </Badge>
          )}
        </div>
        <p className="text-xs sm:text-sm text-slate-400">
          Append-only cryptographic security audit trail recording authentication, consent, and biometric lifecycle events.
        </p>
      </div>

      {/* Search */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <Input
            placeholder="Search by action, status, or IP..."
            className="pl-9 text-xs h-9"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <span className="text-xs text-slate-400">
          Logged Events: <strong className="text-white">{filteredLogs.length}</strong>
        </span>
      </div>

      {/* Audit Log Table */}
      <Card className="border-slate-800 bg-slate-900/80">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Event ID</TableHead>
                <TableHead>Timestamp</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Source IP</TableHead>
                <TableHead>Client User Agent</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredLogs.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-mono text-xs text-slate-400">
                    {truncateId(item.id, 8, 6)}
                  </TableCell>
                  <TableCell className="text-xs text-slate-400">
                    {formatDateTime(item.created_at)}
                  </TableCell>
                  <TableCell className="font-mono text-xs font-semibold text-white">
                    {item.action}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        item.status === "SUCCESS"
                          ? "success"
                          : item.status === "DENIED"
                          ? "warning"
                          : "destructive"
                      }
                      className="text-[10px]"
                    >
                      {item.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-slate-300">
                    {item.ip_address || "Internal"}
                  </TableCell>
                  <TableCell className="text-xs text-slate-500 max-w-xs truncate">
                    {item.user_agent || "N/A"}
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