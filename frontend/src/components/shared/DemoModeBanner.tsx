"use client";

import React from "react";
import { useDemoStore } from "@/store/useDemoStore";
import { Sparkles, X } from "lucide-react";

export function DemoModeBanner() {
  const { isDemoMode, toggleDemoMode } = useDemoStore();

  if (!isDemoMode) return null;

  return (
    <div className="bg-amber-950/80 border-b border-amber-600/40 px-4 py-2 text-xs text-amber-200 flex items-center justify-between shadow-inner">
      <div className="flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-amber-400 flex-shrink-0 animate-pulse" />
        <span>
          <strong className="font-semibold text-amber-300">DEMO EVALUATION MODE:</strong> Rendering isolated sample data for UI inspection. Live backend API calls are not executed for demo records.
        </span>
      </div>
      <button
        onClick={toggleDemoMode}
        className="text-amber-400 hover:text-amber-200 p-1 rounded hover:bg-amber-900/50"
        title="Exit Demo Mode"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
