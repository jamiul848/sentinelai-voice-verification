import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowLeft, ShieldAlert } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-4 text-center">
      <div className="space-y-4 max-w-md">
        <div className="w-16 h-16 rounded-2xl bg-blue-600/20 border border-blue-500/40 text-blue-400 flex items-center justify-center mx-auto">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white">404 - Page Not Found</h1>
        <p className="text-xs sm:text-sm text-slate-400">
          The requested biometric endpoint or interface resource does not exist or has been relocated.
        </p>
        <div className="pt-2">
          <Link href="/">
            <Button className="bg-blue-600 hover:bg-blue-500 text-white gap-2 text-xs">
              <ArrowLeft className="w-4 h-4" />
              <span>Return to Sentinel Voice</span>
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

