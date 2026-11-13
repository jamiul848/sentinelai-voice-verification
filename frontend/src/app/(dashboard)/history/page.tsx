"use client";

import React, { useState } from "react";
import { useDemoStore } from "@/store/useDemoStore";
import { useVerificationHistory } from "@/hooks/useBiometrics";
import { formatDateTime, formatLatency, formatScore, truncateId } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Filter,
  History as HistoryIcon,
  Search,
  Sparkles,
  XCircle,
} from "lucide-react";

const PAGE_SIZE = 25;

export default function HistoryPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);
  const [page, setPage] = useState(0);
  const [filterDecision, setFilterDecision] = useState<"ALL" | "MATCH" | "NO_MATCH">("ALL");
  const [searchTerm, setSearchTerm] = useState("");

  const queryParams = {
    skip: page * PAGE_SIZE,
    limit: PAGE_SIZE,
    decision: filterDecision === "ALL" ? undefined : filterDecision,
    order: "desc" as const,
  };

  const { data, isLoading, error } = useVerificationHistory(queryParams);

  const historyItems = data?.items || [];
  const totalCount = data?.total || 0;
  const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1;

  const filteredItems = historyItems.filter((item) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      item.id.toLowerCase().includes(term) ||
      (item.client_ip && item.client_ip.includes(term))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Verification History</h1>
            {isDemoMode && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <Sparkles className="w-3 h-3" /> DEMO
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Immutable audit log of all 1:1 acoustic speaker verification assessments.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error.message || "Failed to retrieve verification history logs."}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 rounded-xl bg-slate-900 border border-slate-800">
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <Input
            placeholder="Search by Event UUID or IP..."
            className="pl-9 text-xs h-9"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-slate-400 hidden sm:block" />
          <div className="flex rounded-lg border border-slate-700 bg-slate-950 p-0.5 text-xs">
            <button
              onClick={() => {
                setFilterDecision("ALL");
                setPage(0);
              }}
              className={`px-3 py-1 rounded-md transition-colors ${
                filterDecision === "ALL" ? "bg-blue-600 text-white font-medium" : "text-slate-400 hover:text-white"
              }`}
            >
              All Trials
            </button>
            <button
              onClick={() => {
                setFilterDecision("MATCH");
                setPage(0);
              }}
              className={`px-3 py-1 rounded-md transition-colors ${
                filterDecision === "MATCH" ? "bg-emerald-600 text-white font-medium" : "text-slate-400 hover:text-white"
              }`}
            >
              MATCH Only
            </button>
            <button
              onClick={() => {
                setFilterDecision("NO_MATCH");
                setPage(0);
              }}
              className={`px-3 py-1 rounded-md transition-colors ${
                filterDecision === "NO_MATCH" ? "bg-red-600 text-white font-medium" : "text-slate-400 hover:text-white"
              }`}
            >
              NO_MATCH Only
            </button>
          </div>
        </div>
      </div>

      {/* History Table Card */}
      <Card className="border-slate-800 bg-slate-900/90 shadow-2xl">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-12 text-center text-xs text-slate-400 animate-pulse">
              Retrieving verification transaction logs from vault...
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-400 space-y-2">
              <HistoryIcon className="w-8 h-8 mx-auto text-slate-600" />
              <p>No verification events match the selected criteria.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Event UUID</TableHead>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Observed Similarity</TableHead>
                  <TableHead>Threshold</TableHead>
                  <TableHead>Latency</TableHead>
                  <TableHead>Client IP</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredItems.map((item) => (
                  <TableRow key={item.id} className="hover:bg-slate-800/40">
                    <TableCell className="font-mono text-xs text-slate-300">
                      {truncateId(item.id)}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400 whitespace-nowrap">
                      {formatDateTime(item.created_at)}
                    </TableCell>
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
                    <TableCell className="text-xs text-slate-400 whitespace-nowrap">
                      <span className="flex items-center gap-1 font-mono">
                        <Clock className="w-3 h-3 text-slate-500" />
                        {formatLatency(item.processing_time_ms)}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-400">
                      {item.client_ip || "127.0.0.1"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Pagination Controls */}
          {totalCount > PAGE_SIZE && (
            <div className="flex items-center justify-between p-4 border-t border-slate-800 text-xs text-slate-400">
              <span>
                Page {page + 1} of {totalPages} ({totalCount} total events)
              </span>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0 || isLoading}
                  className="h-8 text-xs gap-1"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1 || isLoading}
                  className="h-8 text-xs gap-1"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
