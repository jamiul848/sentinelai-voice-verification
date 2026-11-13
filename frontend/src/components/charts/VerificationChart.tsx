"use client";

import React, { useSyncExternalStore } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface VerificationChartProps {
  data: Array<{
    date: string;
    matches: number;
    nonMatches: number;
  }>;
}

export function VerificationChart({ data }: VerificationChartProps) {
  const isMounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );

  if (!isMounted) {
    return (
      <div className="h-64 w-full flex items-center justify-center bg-slate-900/40 rounded-xl border border-slate-800 text-xs text-slate-500">
        Loading chart visualizer...
      </div>
    );
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="matchesGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="nonMatchesGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
          <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#0f172a",
              borderColor: "#334155",
              borderRadius: "8px",
              color: "#f8fafc",
              fontSize: "12px",
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }}
            formatter={(value) => (value === "matches" ? "Genuine MATCH" : "Impostor / NO_MATCH")}
          />
          <Area
            type="monotone"
            dataKey="matches"
            stroke="#10b981"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#matchesGrad)"
          />
          <Area
            type="monotone"
            dataKey="nonMatches"
            stroke="#ef4444"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#nonMatchesGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
