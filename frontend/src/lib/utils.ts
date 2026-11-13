import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind classes with clsx and twMerge.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Format decimal score to percentage or precision string.
 */
export function formatScore(score: number, decimals: number = 4): string {
  if (typeof score !== "number" || isNaN(score)) return "N/A";
  return score.toFixed(decimals);
}

/**
 * Format percentage.
 */
export function formatPercent(value: number, decimals: number = 1): string {
  if (typeof value !== "number" || isNaN(value)) return "0.0%";
  return `${(value * 100).toFixed(decimals)}%`;
}

/**
 * Format milliseconds to human readable string (e.g. 1,240 ms or 1.24 s).
 */
export function formatLatency(ms: number): string {
  if (typeof ms !== "number" || isNaN(ms)) return "0 ms";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

/**
 * Format ISO datetime string to localized human format.
 */
export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return "N/A";
  try {
    const d = new Date(isoString);
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(d);
  } catch {
    return isoString;
  }
}

/**
 * Truncate long UUIDs or hashes for UI display.
 */
export function truncateId(id: string, startChars: number = 8, endChars: number = 6): string {
  if (!id || id.length <= startChars + endChars) return id;
  return `${id.slice(0, startChars)}...${id.slice(-endChars)}`;
}

/**
 * Format byte count to human-readable string.
 */
export function formatBytes(bytes: number, decimals: number = 2): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

