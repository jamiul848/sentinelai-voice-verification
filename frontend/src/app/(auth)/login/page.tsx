"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { authService } from "@/lib/api/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, Eye, EyeOff, Lock, Mail, Shield } from "lucide-react";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address").min(1, "Email is required"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectParam = searchParams.get("redirect");

  const { isAuthenticated, isLoading, user, setAuth } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [retryAfter, setRetryAfter] = useState<number | null>(null);

  // If already logged in, redirect away from auth page
  useEffect(() => {
    if (!isLoading && isAuthenticated && user) {
      const hasAdminRole = user.roles?.some((r) => r === "ADMIN" || r === "SUPER_ADMIN");
      const target = redirectParam || (hasAdminRole ? "/admin/dashboard" : "/dashboard");
      router.replace(target);
    }
  }, [isLoading, isAuthenticated, user, redirectParam, router]);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const onSubmit = async (values: LoginFormValues) => {
    setApiError(null);
    setRetryAfter(null);

    try {
      const data = await authService.login(values);
      setAuth(data.user, data.access_token, data.refresh_token);

      const hasAdminRole = data.user?.roles?.some(
        (r) => r === "ADMIN" || r === "SUPER_ADMIN"
      );
      const targetDestination = redirectParam || (hasAdminRole ? "/admin/dashboard" : "/dashboard");
      router.push(targetDestination);
    } catch (err: any) {
      if (err.status === 429 && err.retryAfter) {
        setRetryAfter(err.retryAfter);
        setApiError(`Rate limit exceeded. Please wait ${err.retryAfter} seconds before trying again.`);
      } else {
        setApiError(err.message || "Invalid email or password.");
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <Link href="/" className="inline-flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
              <Shield className="w-6 h-6" />
            </div>
            <span className="font-extrabold text-xl tracking-wider text-white">SENTINEL VOICE</span>
          </Link>
          <p className="text-xs text-slate-400 tracking-wide uppercase font-medium">Biometric Portal Access</p>
        </div>

        <Card className="border-slate-800 bg-slate-900/90 shadow-2xl">
          <CardHeader className="space-y-1">
            <CardTitle className="text-xl font-bold text-white">Account Login</CardTitle>
            <CardDescription className="text-slate-400 text-xs">
              Enter your credentials to access voice enrollment and verification services.
            </CardDescription>
          </CardHeader>

          <CardContent className="pt-4">
            {apiError && (
              <div className="mb-4 p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{apiError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  Email Address
                </label>
                <Input
                  type="email"
                  placeholder="name@sentinelvoice.io"
                  {...register("email")}
                  error={errors.email?.message}
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-slate-400" />
                    Password
                  </label>
                  <Link
                    href="/forgot-password"
                    className="text-xs text-blue-400 hover:text-blue-300 hover:underline"
                  >
                    Forgot password?
                  </Link>
                </div>
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
              </div>

              <Button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2.5 mt-2"
                isLoading={isSubmitting}
                disabled={retryAfter !== null && retryAfter > 0}
              >
                Sign In
              </Button>
            </form>

            <div className="mt-6 pt-4 border-t border-slate-800 text-center text-xs text-slate-400">
              Don&apos;t have an account?{" "}
              <Link href="/register" className="text-blue-400 hover:text-blue-300 font-semibold hover:underline">
                Create Account
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-500 text-xs font-mono">
          Loading login portal...
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
