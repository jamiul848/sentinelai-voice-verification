import React from "react";
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  FileCheck,
  Lock,
  Mic,
  Shield,
  Sliders,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-blue-600 selection:text-white">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
              <Shield className="w-5 h-5" />
            </div>
            <span className="font-bold text-base tracking-wider text-white">SENTINEL VOICE</span>
          </div>

          <nav className="hidden md:flex items-center gap-8 text-sm text-slate-300">
            <a href="#how-it-works" className="hover:text-white transition-colors">
              How It Works
            </a>
            <a href="#capabilities" className="hover:text-white transition-colors">
              Capabilities
            </a>
            <a href="#security" className="hover:text-white transition-colors">
              Biometric Security
            </a>
            <a href="#tech" className="hover:text-white transition-colors">
              Architecture
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <Link href="/login">
              <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white">
                Log In
              </Button>
            </Link>
            <Link href="/register">
              <Button size="sm" className="bg-blue-600 hover:bg-blue-500 text-white shadow-sm">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative pt-24 pb-20 md:pt-32 md:pb-28 overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-900/20 via-slate-950 to-slate-950 -z-10" />
          <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center space-y-8">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/30 bg-blue-500/10 text-xs font-semibold text-blue-300 tracking-wide">
              <Shield className="w-3.5 h-3.5 text-blue-400" />
              <span>AI-POWERED SPEAKER VERIFICATION PLATFORM</span>
            </div>

            <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
              Verify Identity <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-sky-300">Through Voice.</span>
            </h1>

            <p className="max-w-2xl mx-auto text-base sm:text-xl text-slate-400 leading-relaxed">
              Secure speaker verification powered by AI-driven voice embeddings and encrypted biometric storage.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
              <Link href="/register" className="w-full sm:w-auto">
                <Button size="lg" className="w-full sm:w-auto bg-blue-600 hover:bg-blue-500 text-white px-8 gap-2 glow-primary">
                  <span>Get Started</span>
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
              <a href="#how-it-works" className="w-full sm:w-auto">
                <Button variant="secondary" size="lg" className="w-full sm:w-auto px-8">
                  Explore Platform
                </Button>
              </a>
            </div>

            {/* Architecture Invariants Badge Strip */}
            <div className="pt-12 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto text-left">
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
                <p className="text-xs text-slate-400 font-medium">Neural Backbone</p>
                <p className="text-sm font-semibold text-white mt-1">192D ECAPA-TDNN</p>
              </div>
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
                <p className="text-xs text-slate-400 font-medium">Biometric Storage</p>
                <p className="text-sm font-semibold text-white mt-1">AES-256-GCM Envelope</p>
              </div>
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
                <p className="text-xs text-slate-400 font-medium">Decision Boundary</p>
                <p className="text-sm font-semibold text-white mt-1">Dynamic EER Calibrated</p>
              </div>
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
                <p className="text-xs text-slate-400 font-medium">Profile Deletion</p>
                <p className="text-sm font-semibold text-white mt-1">NIST SP 800-88 Shredding</p>
              </div>
            </div>
          </div>
        </section>

        {/* Section 2: How It Works */}
        <section id="how-it-works" className="py-20 border-t border-slate-800/80 bg-slate-900/30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16 space-y-3">
              <h2 className="text-xs font-bold text-blue-400 uppercase tracking-widest">Acoustic Pipeline</h2>
              <p className="text-3xl font-bold text-white tracking-tight">How Speaker Verification Works</p>
              <p className="text-sm text-slate-400">
                A deterministic, mathematically grounded 1:1 claimant verification workflow.
              </p>
            </div>

            <div className="grid md:grid-cols-4 gap-6">
              <Card className="bg-slate-900/60 border-slate-800 relative">
                <CardContent className="p-6 space-y-4">
                  <div className="w-10 h-10 rounded-lg bg-blue-600/20 text-blue-400 flex items-center justify-center font-bold text-sm">
                    01
                  </div>
                  <h3 className="text-base font-semibold text-white">Audio Capture & Normalization</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Acoustic recordings are sampled, converted to mono 16kHz PCM, and screened for minimum RMS amplitude and duration.
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-slate-900/60 border-slate-800 relative">
                <CardContent className="p-6 space-y-4">
                  <div className="w-10 h-10 rounded-lg bg-blue-600/20 text-blue-400 flex items-center justify-center font-bold text-sm">
                    02
                  </div>
                  <h3 className="text-base font-semibold text-white">ECAPA-TDNN Feature Extraction</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Pretrained temporal delay neural networks extract continuous 192-dimensional speaker embeddings capturing vocal tract geometry.
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-slate-900/60 border-slate-800 relative">
                <CardContent className="p-6 space-y-4">
                  <div className="w-10 h-10 rounded-lg bg-blue-600/20 text-blue-400 flex items-center justify-center font-bold text-sm">
                    03
                  </div>
                  <h3 className="text-base font-semibold text-white">Cosine Scoring & Thresholding</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Calculates cosine similarity between the probe embedding and reference centroid against dynamically calibrated operating thresholds.
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-slate-900/60 border-slate-800 relative">
                <CardContent className="p-6 space-y-4">
                  <div className="w-10 h-10 rounded-lg bg-blue-600/20 text-blue-400 flex items-center justify-center font-bold text-sm">
                    04
                  </div>
                  <h3 className="text-base font-semibold text-white">Binary MATCH Decision</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Produces a strict MATCH or NO_MATCH decision, recording cryptographic audit event timestamps without saving probe audio.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* Section 3: Platform Capabilities */}
        <section id="capabilities" className="py-20 border-t border-slate-800/80">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16 space-y-3">
              <h2 className="text-xs font-bold text-blue-400 uppercase tracking-widest">Capabilities</h2>
              <p className="text-3xl font-bold text-white tracking-tight">Engineered for Enterprise Biometrics</p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              <div className="space-y-3 p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80">
                <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                  <Mic className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-semibold text-white">Secure Voice Enrollment</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Requires 3 distinct utterances, validates acoustic quality, computes intra-session consistency, and forms reference centroids.
                </p>
              </div>

              <div className="space-y-3 p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-semibold text-white">AI-Powered Speaker Verification</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Real-time 1:1 claimant verification evaluates incoming probes against reference voiceprints in ~1.2s average latency.
                </p>
              </div>

              <div className="space-y-3 p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                  <Lock className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-semibold text-white">Encrypted Biometric Templates</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Reference vectors are stored in AES-256-GCM encrypted envelopes with per-profile DEKs. Raw vectors never hit database columns unencrypted.
                </p>
              </div>

              <div className="space-y-3 p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80">
                <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                  <Sliders className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-semibold text-white">Dynamic Operating Thresholds</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Calibrated decision thresholds are queried dynamically from PostgreSQL, allowing zero-downtime operational security level shifts.
                </p>
              </div>

              <div className="space-y-3 p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80">
                <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                  <FileCheck className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-semibold text-white">Tamper-Resistant Audit Logging</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Every verification attempt, authentication event, and administrative status modification produces append-only audit records.
                </p>
              </div>

              <div className="space-y-3 p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Shield className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-semibold text-white">Privacy-First Architecture</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Full compliance with GDPR and BIPA mandates: strict consent gating before enrollment, with one-click cryptographic profile shredding.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Section 4: Security & Privacy */}
        <section id="security" className="py-20 border-t border-slate-800/80 bg-slate-900/20">
          <div className="max-w-5xl mx-auto px-4 sm:px-6">
            <div className="rounded-3xl border border-slate-800 bg-gradient-to-b from-slate-900/80 to-slate-950 p-8 sm:p-12 space-y-8">
              <div className="space-y-2">
                <span className="text-xs font-bold text-emerald-400 uppercase tracking-widest">Compliance & Crypto Standards</span>
                <h2 className="text-2xl sm:text-3xl font-bold text-white">NIST SP 800-88 & Envelope Encryption</h2>
              </div>

              <div className="grid sm:grid-cols-2 gap-6 text-sm">
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-2">
                  <h4 className="font-semibold text-white flex items-center gap-2">
                    <Lock className="w-4 h-4 text-blue-400" />
                    Two-Tier Key Hierarchy
                  </h4>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Master Key Encryption Key (KEK) wraps individual Data Encryption Keys (DEKs) using AES-256-GCM with authenticated tags, preventing key compromise exposure.
                  </p>
                </div>

                <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-2">
                  <h4 className="font-semibold text-white flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    NIST SP 800-88 Shredding
                  </h4>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Profile revocation triggers multi-pass cryptographic overwriting (0x00, 0xFF, random bytes) of on-disk containers before physical unlinking.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Call to Action */}
        <section className="py-20 border-t border-slate-800/80 text-center">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 space-y-6">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Ready to verify speaker identity with AI?
            </h2>
            <p className="text-sm sm:text-base text-slate-400 max-w-xl mx-auto">
              Register an account to test voice enrollment, evaluate genuine vs. impostor verification, and inspect real-time audit logs.
            </p>
            <div className="pt-2">
              <Link href="/register">
                <Button size="lg" className="bg-blue-600 hover:bg-blue-500 text-white px-8 glow-primary">
                  Create Free Account
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8 bg-slate-950 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-blue-500" />
            <span className="font-semibold text-slate-400">Sentinel Voice</span>
            <span>— AI-Powered Speaker Verification Platform</span>
          </div>
          <p>© 2026 Sentinel Voice. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
