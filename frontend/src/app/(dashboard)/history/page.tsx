"use client";

import React, { useEffect, useState } from "react";
import { biometricsService } from "@/lib/api/services/biometrics.service";
import { useDemoStore } from "@/store/useDemoStore";
import { DEMO_VERIFICATION_HISTORY } from "@/config/demo";
import { VerificationHistoryItem } from "@/types";
import { formatDateTime, formatLatency, formatScore, truncateId } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Filter,
  History as HistoryIcon,
  Search,
  Sparkles,
  XCircle,
} from "lucide-react";

export default function HistoryPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  const [history, setHistory] = useState<VerificationHistoryItem[]>([]);
  const [filterDecision, setFilterDecision] = useState<"ALL" | "MATCH" | "NO_MATCH">("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [_isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    async function loadHistory() {
      setIsLoading(true);
      setErrorMsg(null);

      if (isDemoMode) {
        setHistory(DEMO_VERIFICATION_HISTORY);
        setIsLoading(false);
        return;
      }

      try {
        const res = await biometricsService.getVerificationHistory({ limit: 50 });
        setHistory(res?.items || []);
      } catch (err: any) {
        setErrorMsg(err.message || "Failed to retrieve verification history logs.");
      } finally {
        setIsLoading(false);
      }
    }

    loadHistory();
  }, [isDemoMode]);

  const filteredItems = history.filter((item) => {
    const matchesDecision =
      filterDecision === "ALL" ? true : item.decision === filterDecision;
    const matchesSearch =
      searchTerm.trim() === ""
        ? true
        : item.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
          (item.client_ip && item.client_ip.includes(searchTerm));
    return matchesDecision && matchesSearch;
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
            Immutable audit trail of all 1:1 acoustic speaker verification transactions.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
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

        <div className="flex items-center gap-1.5 w-full sm:w-auto">
          <span className="text-xs text-slate-400 font-medium mr-1 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" /> Filter:
          </span>
          <button
            onClick={() => setFilterDecision("ALL")}
            className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors ${
              filterDecision === "ALL"
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            All ({history.length})
          </button>
          <button
            onClick={() => setFilterDecision("MATCH")}
            className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors ${
              filterDecision === "MATCH"
                ? "bg-emerald-600 text-white"
                : "bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            Matches ({history.filter((h) => h.decision === "MATCH").length})
          </button>
          <button
            onClick={() => setFilterDecision("NO_MATCH")}
            className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors ${
              filterDecision === "NO_MATCH"
                ? "bg-red-600 text-white"
                : "bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            Rejections ({history.filter((h) => h.decision === "NO_MATCH").length})
          </button>
        </div>
      </div>

      {/* Main Table Card */}
      <Card className="border-slate-800 bg-slate-900/80">
        <CardContent className="p-0">
          {filteredItems.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-400 space-y-2">
              <HistoryIcon className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="font-semibold text-slate-300">No verification events found.</p>
              <p>Adjust your search criteria or submit a live verification trial.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Event UUID</TableHead>
                  <TableHead>Execution Date</TableHead>
                  <TableHead>Outcome</TableHead>
                  <TableHead>Observed Score</TableHead>
                  <TableHead>Threshold</TableHead>
                  <TableHead>Latency</TableHead>
                  <TableHead>Client IP</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredItems.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono text-xs text-slate-300 font-medium">
                      {truncateId(item.id, 10, 8)}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400">
                      {formatDateTime(item.created_at)}
                    </TableCell>
                    <TableCell>
                      {item.decision === "MATCH" ? (
                        <Badge variant="success" className="gap-1 text-[11px]">
                          <CheckCircle2 className="w-3 h-3" /> MATCH
                        </Badge>
                      ) : (
                        <Badge variant="destructive" className="gap-1 text-[11px]">
                          <XCircle className="w-3 h-3" /> NO_MATCH
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs font-semibold">
                      <span
                        className={
                          item.similarity_score >= item.applied_threshold
                            ? "text-emerald-400"
                            : "text-red-400"
                        }
                      >
                        {formatScore(item.similarity_score)}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-400">
                      {formatScore(item.applied_threshold)}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {formatLatency(item.processing_time_ms)}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-500">
                      {item.client_ip || "127.0.0.1"}
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
