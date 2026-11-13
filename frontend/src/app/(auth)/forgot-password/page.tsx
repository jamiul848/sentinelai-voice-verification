"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Info, Mail, Shield } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
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
          <p className="text-xs text-slate-400 tracking-wide uppercase font-medium">Credential Recovery</p>
        </div>

        <Card className="border-slate-800 bg-slate-900/90 shadow-2xl">
          <CardHeader className="space-y-1">
            <CardTitle className="text-xl font-bold text-white">Reset Password</CardTitle>
            <CardDescription className="text-slate-400 text-xs">
              Enter your registered email address to receive password recovery instructions.
            </CardDescription>
          </CardHeader>

          <CardContent className="pt-4 space-y-4">
            <div className="p-3.5 rounded-lg bg-blue-950/40 border border-blue-800/60 text-blue-200 text-xs flex items-start gap-2.5 leading-relaxed">
              <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
              <span>
                <strong>Security Notice:</strong> Automated password reset email delivery depends on configured SMTP gateways. Contact your security administrator if self-service reset is unavailable.
              </span>
            </div>

            {submitted ? (
              <div className="space-y-4 text-center py-4">
                <p className="text-xs text-slate-300">
                  If an account exists for <strong className="text-white">{email}</strong>, recovery instructions have been queued.
                </p>
                <Link href="/login">
                  <Button variant="secondary" className="w-full">
                    Return to Login
                  </Button>
                </Link>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    Account Email
                  </label>
                  <Input
                    type="email"
                    required
                    placeholder="user@sentinelvoice.io"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>

                <Button type="submit" className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold">
                  Send Recovery Link
                </Button>
              </form>
            )}

            <div className="pt-2 text-center">
              <Link
                href="/login"
                className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Login</span>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

