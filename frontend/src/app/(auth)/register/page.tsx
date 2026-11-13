"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { authService } from "@/lib/api/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, CheckCircle2, Eye, EyeOff, Lock, Mail, Shield, User as UserIcon } from "lucide-react";

const registerSchema = z
  .object({
    full_name: z.string().min(2, "Full name must be at least 2 characters").max(150),
    email: z.string().email("Please enter a valid email address").max(255),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Password must include at least one uppercase letter")
      .regex(/[a-z]/, "Password must include at least one lowercase letter")
      .regex(/[0-9]/, "Password must include at least one number")
      .regex(/[^A-Za-z0-9]/, "Password must include at least one special character"),
    password_confirm: z.string().min(1, "Please confirm your password"),
    accept_privacy_terms: z.boolean().refine((val) => val === true, {
      message: "You must accept the biometric privacy terms to proceed",
    }),
  })
  .refine((data) => data.password === data.password_confirm, {
    message: "Passwords do not match",
    path: ["password_confirm"],
  });

type RegisterFormValues = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, user } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // If already authenticated, redirect to appropriate dashboard
  useEffect(() => {
    if (!isLoading && isAuthenticated && user) {
      const hasAdminRole = user.roles?.some((r) => r === "ADMIN" || r === "SUPER_ADMIN");
      router.replace(hasAdminRole ? "/admin/dashboard" : "/dashboard");
    }
  }, [isLoading, isAuthenticated, user, router]);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: "",
      email: "",
      password: "",
      password_confirm: "",
      accept_privacy_terms: false,
    },
  });

  const watchedPassword = watch("password") || "";

  // Password Strength Indicators matching backend Argon2id validation
  const rules = [
    { label: "8+ characters", met: watchedPassword.length >= 8 },
    { label: "Uppercase letter", met: /[A-Z]/.test(watchedPassword) },
    { label: "Lowercase letter", met: /[a-z]/.test(watchedPassword) },
    { label: "Digit (0-9)", met: /[0-9]/.test(watchedPassword) },
    { label: "Special symbol", met: /[^A-Za-z0-9]/.test(watchedPassword) },
  ];

  const onSubmit = async (values: RegisterFormValues) => {
    setApiError(null);
    try {
      const res = await authService.register(values);
      setSuccessMsg(res.message || "Account registered successfully. Redirecting to login...");
      setTimeout(() => {
        router.push("/login");
      }, 1500);
    } catch (err: any) {
      setApiError(err.message || "Registration failed. Please check the provided information.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <Link href="/" className="inline-flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
              <Shield className="w-6 h-6" />
            </div>
            <span className="font-extrabold text-xl tracking-wider text-white">SENTINEL VOICE</span>
          </Link>
          <p className="text-xs text-slate-400 tracking-wide uppercase font-medium">New User Registration</p>
        </div>

        <Card className="border-slate-800 bg-slate-900/90 shadow-2xl">
          <CardHeader className="space-y-1">
            <CardTitle className="text-xl font-bold text-white">Create Account</CardTitle>
            <CardDescription className="text-slate-400 text-xs">
              Register an identity to participate in AI speaker verification and biometric defense.
            </CardDescription>
          </CardHeader>

          <CardContent className="pt-4">
            {apiError && (
              <div className="mb-4 p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{apiError}</span>
              </div>
            )}

            {successMsg && (
              <div className="mb-4 p-3 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span>{successMsg}</span>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <UserIcon className="w-3.5 h-3.5 text-slate-400" />
                  Full Name
                </label>
                <Input
                  placeholder="Dr. Sarah Sentinel"
                  {...register("full_name")}
                  error={errors.full_name?.message}
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  Email Address
                </label>
                <Input
                  type="email"
                  placeholder="sarah@sentinelvoice.io"
                  {...register("email")}
                  error={errors.email?.message}
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-slate-400" />
                  Password
                </label>
                <div className="relative">
                  <Input
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••••••"
                    {...register("password")}
                    error={errors.password?.message}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-200"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>

                {/* Password strength badge hints */}
                <div className="pt-2 flex flex-wrap gap-1.5">
                  {rules.map((r, i) => (
                    <span
                      key={i}
                      className={`text-[10px] px-2 py-0.5 rounded-full font-medium transition-colors ${
                        r.met
                          ? "bg-emerald-950/70 border border-emerald-800 text-emerald-400"
                          : "bg-slate-800 text-slate-500 border border-slate-700/60"
                      }`}
                    >
                      {r.label}
                    </span>
                  ))}
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-slate-400" />
                  Confirm Password
                </label>
                <Input
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••••••"
                  {...register("password_confirm")}
                  error={errors.password_confirm?.message}
                />
              </div>

              <div className="pt-2 space-y-1">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    className="mt-0.5 rounded border-slate-700 bg-slate-950 text-blue-600 focus:ring-blue-500"
                    {...register("accept_privacy_terms")}
                  />
                  <span className="text-[11px] text-slate-400 leading-snug">
                    I consent to the capture, 192D neural embedding transformation, and AES-256-GCM envelope
                    encryption of my voice acoustic vectors under GDPR & Illinois BIPA compliance rules.
                  </span>
                </label>
                {errors.accept_privacy_terms && (
                  <p className="text-[11px] text-red-400 pl-6">{errors.accept_privacy_terms.message}</p>
                )}
              </div>

              <Button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2.5 mt-3"
                isLoading={isSubmitting}
              >
                Create Account
              </Button>
            </form>

            <div className="mt-6 pt-4 border-t border-slate-800 text-center text-xs text-slate-400">
              Already have an account?{" "}
              <Link href="/login" className="text-blue-400 hover:text-blue-300 font-semibold hover:underline">
                Sign In
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
