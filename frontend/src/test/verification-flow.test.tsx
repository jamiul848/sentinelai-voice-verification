import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import VerificationPage from "@/app/(dashboard)/verification/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { consentService } from "@/lib/api/services/consent.service";
import { biometricsService } from "@/lib/api/services/biometrics.service";
import { useDemoStore } from "@/store/useDemoStore";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/verification",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api/services/consent.service", () => ({
  consentService: {
    getStatus: vi.fn(),
  },
}));

vi.mock("@/lib/api/services/biometrics.service", () => ({
  biometricsService: {
    getProfile: vi.fn(),
    verifyVoice: vi.fn(),
  },
}));

// Mock AudioRecorder to simulate probe capture
vi.mock("@/components/voice/AudioRecorder", () => ({
  AudioRecorder: ({ onRecordingComplete, sampleLabel }: any) => (
    <div data-testid="mock-audio-recorder">
      <span>{sampleLabel}</span>
      <button
        onClick={() => {
          const fakeProbe = new File(["fake-probe-wav"], "probe.wav", { type: "audio/wav" });
          onRecordingComplete(fakeProbe);
        }}
      >
        Simulate Record Probe
      </button>
    </div>
  ),
}));

describe("Phase 8C - Speaker Verification Evaluation Flow", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    useDemoStore.setState({ isDemoMode: false });
  });

  it("blocks verification and displays enrollment prompt if user has no active profile", async () => {
    (consentService.getStatus as any).mockResolvedValueOnce({ has_active_consent: true });
    (biometricsService.getProfile as any).mockResolvedValueOnce(null);

    render(
      <QueryClientProvider client={queryClient}>
        <VerificationPage />
      </QueryClientProvider>
    );

    expect(await screen.findByText(/Active Voice Profile Required/i)).toBeInTheDocument();
    expect(screen.getByText(/Begin Voice Enrollment/i)).toBeInTheDocument();
  });

  it("renders live voice probe recorder when profile is active and consent is granted", async () => {
    (consentService.getStatus as any).mockResolvedValueOnce({ has_active_consent: true });
    (biometricsService.getProfile as any).mockResolvedValueOnce({
      id: "prof-active-1",
      status: "ACTIVE",
      sample_count: 3,
    });

    render(
      <QueryClientProvider client={queryClient}>
        <VerificationPage />
      </QueryClientProvider>
    );

    expect(await screen.findByText(/Live Voice Probe/i)).toBeInTheDocument();
    expect(screen.getByText(/Verification Probe Utterance/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Verify Voiceprint/i })).toBeDisabled();
  });

  it("submits probe and renders authentic MATCH decision card", async () => {
    (consentService.getStatus as any).mockResolvedValueOnce({ has_active_consent: true });
    (biometricsService.getProfile as any).mockResolvedValueOnce({
      id: "prof-active-1",
      status: "ACTIVE",
      sample_count: 3,
    });

    (biometricsService.verifyVoice as any).mockResolvedValueOnce({
      verification_id: "verif-tx-999",
      decision: "MATCH",
      is_match: true,
      similarity_score: 0.88421,
      applied_threshold: 0.405898,
      processing_time_ms: 285.4,
      model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
      threshold_version: "v1.0.0-eer-calibrated",
      timestamp: "2026-11-13T12:30:00Z",
    });

    render(
      <QueryClientProvider client={queryClient}>
        <VerificationPage />
      </QueryClientProvider>
    );

    // Record probe
    const recordBtn = await screen.findByText(/Simulate Record Probe/i);
    fireEvent.click(recordBtn);

    const verifyBtn = screen.getByRole("button", { name: /Verify Voiceprint/i });
    expect(verifyBtn).toBeEnabled();
    fireEvent.click(verifyBtn);

    // Assert MATCH outcome
    await waitFor(() => {
      expect(screen.getByText(/AUTHENTIC MATCH/i)).toBeInTheDocument();
    });

    expect(screen.getByText("0.8842")).toBeInTheDocument();
    expect(screen.getByText("0.4059")).toBeInTheDocument();
    expect(screen.getByText("285 ms")).toBeInTheDocument();
    expect(screen.getByText(/v1.0.0-eer-calibrated/i)).toBeInTheDocument();
    expect(screen.getByText(/Verify Again/i)).toBeInTheDocument();
  });

  it("submits probe and renders NO_MATCH impostor rejection card", async () => {
    (consentService.getStatus as any).mockResolvedValueOnce({ has_active_consent: true });
    (biometricsService.getProfile as any).mockResolvedValueOnce({
      id: "prof-active-1",
      status: "ACTIVE",
      sample_count: 3,
    });

    (biometricsService.verifyVoice as any).mockResolvedValueOnce({
      verification_id: "verif-tx-111",
      decision: "NO_MATCH",
      is_match: false,
      similarity_score: 0.1852,
      applied_threshold: 0.405898,
      processing_time_ms: 240.1,
      model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
      threshold_version: "v1.0.0-eer-calibrated",
      timestamp: "2026-11-13T12:35:00Z",
    });

    render(
      <QueryClientProvider client={queryClient}>
        <VerificationPage />
      </QueryClientProvider>
    );

    const recordBtn = await screen.findByText(/Simulate Record Probe/i);
    fireEvent.click(recordBtn);

    const verifyBtn = screen.getByRole("button", { name: /Verify Voiceprint/i });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(screen.getByText(/NO MATCH \/ IMPOSTOR REJECTED/i)).toBeInTheDocument();
    });

    expect(screen.getByText("0.1852")).toBeInTheDocument();
  });
});
