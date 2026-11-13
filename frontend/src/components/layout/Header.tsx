"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";
import { useDemoStore } from "@/store/useDemoStore";
import { authService } from "@/lib/api/services/auth.service";
import {
  ChevronDown,
  LogOut,
  Menu,
  Sparkles,
  User as UserIcon,
} from "lucide-react";

interface HeaderProps {
  onToggleMobileMenu: () => void;
  title?: string;
}

export function Header({ onToggleMobileMenu, title }: HeaderProps) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const { isDemoMode, toggleDemoMode } = useDemoStore();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch {
      // Continue client cleanup even if network fails
    } finally {
      clearAuth();
      router.push("/login");
    }
  };

  return (
    <header className="h-16 flex items-center justify-between px-4 sm:px-6 border-b border-slate-800 bg-slate-900/90 backdrop-blur-md sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleMobileMenu}
          className="lg:hidden p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        {title && <h1 className="text-base sm:text-lg font-semibold text-white tracking-tight">{title}</h1>}
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        {/* Demo Mode Toggle */}
        <button
          onClick={toggleDemoMode}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border transition-all ${
            isDemoMode
              ? "bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm"
              : "bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200"
          }`}
          title="Toggle Demo Mode with preloaded evaluation fixtures"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Demo Data: {isDemoMode ? "ON" : "OFF"}</span>
        </button>

        {/* Operational Status indicator */}
        <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs text-slate-300">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>API 0.1.0 Online</span>
        </div>

        {/* User Account Menu */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-800 text-slate-300 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-blue-600/30 border border-blue-500/40 flex items-center justify-center text-xs font-semibold text-blue-300">
              {user?.full_name?.charAt(0) || "U"}
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {dropdownOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setDropdownOpen(false)} />
              <div className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-700 bg-slate-900 py-1.5 shadow-2xl z-50 text-slate-200 animate-in fade-in zoom-in-95 duration-150">
                <div className="px-4 py-2 border-b border-slate-800">
                  <p className="text-xs font-semibold text-white truncate">{user?.full_name || "User"}</p>
                  <p className="text-[11px] text-slate-400 truncate">{user?.email || "No email"}</p>
                </div>
                <button
                  onClick={() => {
                    setDropdownOpen(false);
                    router.push("/profile");
                  }}
                  className="w-full flex items-center gap-2.5 px-4 py-2 text-xs hover:bg-slate-800 transition-colors text-left"
                >
                  <UserIcon className="w-4 h-4 text-slate-400" />
                  <span>My Profile</span>
                </button>
                <button
                  onClick={() => {
                    setDropdownOpen(false);
                    handleLogout();
                  }}
                  className="w-full flex items-center gap-2.5 px-4 py-2 text-xs text-red-400 hover:bg-red-500/10 transition-colors text-left border-t border-slate-800/80 mt-1"
                >
                  <LogOut className="w-4 h-4 text-red-400" />
                  <span>Sign Out</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
