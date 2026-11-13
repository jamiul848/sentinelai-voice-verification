import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border border-transparent bg-primary/20 text-blue-300 border-blue-500/30",
        secondary:
          "border border-slate-700 bg-slate-800 text-slate-300",
        success:
          "border border-emerald-500/30 bg-emerald-500/15 text-emerald-400",
        warning:
          "border border-amber-500/30 bg-amber-500/15 text-amber-300",
        destructive:
          "border border-red-500/30 bg-red-500/15 text-red-400",
        outline:
          "border border-slate-700 text-slate-300",
        cyber:
          "border border-sky-400/40 bg-sky-950/60 text-sky-300 font-mono tracking-wider",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

