"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/useAuthStore";
import {
  Activity,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  FileText,
  History,
  LayoutDashboard,
  Mic,
  Shield,
  Sliders,
  Users,
  Settings as SettingsIcon,
} from "lucide-react";

interface SidebarProps {
  isAdmin?: boolean;
  onCloseMobile?: () => void;
}

export function Sidebar({ isAdmin = false, onCloseMobile }: SidebarProps) {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);

  const userNavItems = [
    { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
    { name: "Voice Enrollment", href: "/enrollment", icon: Mic },
    { name: "Voice Verification", href: "/verification", icon: CheckCircle2 },
    { name: "My Voice Profile", href: "/profile", icon: Shield },
    { name: "Verification History", href: "/history", icon: History },
    { name: "Settings", href: "/settings", icon: SettingsIcon },
  ];

  const adminNavItems = [
    { name: "Admin Overview", href: "/admin/dashboard", icon: LayoutDashboard },
    { name: "User Management", href: "/admin/users", icon: Users },
    { name: "Verification Analytics", href: "/admin/analytics", icon: BarChart3 },
    { name: "Threshold Config", href: "/admin/thresholds", icon: Sliders },
    { name: "Audit Logs", href: "/admin/audit-logs", icon: FileText },
    { name: "System Health", href: "/admin/system-health", icon: Activity },
  ];

  const navItems = isAdmin ? adminNavItems : userNavItems;
  const isUserAdmin = user?.roles?.some((r) => r === "ADMIN" || r === "SUPER_ADMIN");

  return (
    <aside className="w-64 flex-shrink-0 flex flex-col h-full bg-slate-900 border-r border-slate-800 text-slate-200">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-slate-800 gap-3">
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-blue-600/20 border border-blue-500/40 text-blue-400">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <span className="font-bold text-sm text-white tracking-wide block">SENTINEL VOICE</span>
          <span className="text-[10px] text-blue-400 tracking-wider font-semibold block uppercase">
            {isAdmin ? "Admin Console" : "Biometric Portal"}
          </span>
        </div>
      </div>

      {/* Switcher between User Portal & Admin Console (if user is Admin) */}
      {isUserAdmin && (
        <div className="p-3 mx-3 mt-3 rounded-lg bg-slate-800/60 border border-slate-700/60">
          <div className="text-[11px] text-slate-400 font-medium mb-1.5 px-1">WORKSPACE MODE</div>
          <div className="grid grid-cols-2 gap-1 text-xs font-medium">
            <Link
              href="/dashboard"
              className={cn(
                "px-2 py-1.5 rounded text-center transition-colors",
                !isAdmin
                  ? "bg-blue-600 text-white font-semibold shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/40"
              )}
            >
              User App
            </Link>
            <Link
              href="/admin/dashboard"
              className={cn(
                "px-2 py-1.5 rounded text-center transition-colors",
                isAdmin
                  ? "bg-purple-600 text-white font-semibold shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/40"
              )}
            >
              Admin
            </Link>
          </div>
        </div>
      )}

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          {isAdmin ? "Fleet Operations" : "Verification Suite"}
        </div>
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onCloseMobile}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group",
                isActive
                  ? "bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm"
                  : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
              )}
            >
              <Icon
                className={cn(
                  "w-4 h-4 transition-colors",
                  isActive ? "text-blue-400" : "text-slate-400 group-hover:text-slate-200"
                )}
              />
              <span className="flex-1">{item.name}</span>
              {isActive && <ChevronRight className="w-4 h-4 text-blue-400/80" />}
            </Link>
          );
        })}
      </nav>

      {/* User Profile Bar at bottom */}
      <div className="p-3 border-t border-slate-800 bg-slate-900/60">
        <div className="flex items-center gap-3 px-2 py-1.5">
          <div className="w-8 h-8 rounded-full bg-blue-900/60 border border-blue-500/40 flex items-center justify-center text-xs font-bold text-blue-300">
            {user?.full_name?.charAt(0) || "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-white truncate">{user?.full_name || "Authenticated User"}</p>
            <p className="text-[11px] text-slate-400 truncate">{user?.email || "user@sentinelvoice.io"}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
