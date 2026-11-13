import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import ProfilePage from "@/app/(dashboard)/profile/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { biometricsService } from "@/lib/api/services/biometrics.service";
import { consentService } from "@/lib/api/services/consent.service";
import { useDemoStore } from "@/store/useDemoStore";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/profile",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api/services/biometrics.service", () => ({
  biometricsService: {
    getProfile: vi.fn(),
    revokeProfile: vi.fn(),
    reEnrollVoice: vi.fn(),
  },
}));

vi.mock("@/lib/api/services/consent.service", () => ({
  consentService: {
    getStatus: vi.fn(),
  },
}));

// Mock AudioRecorder for re-enrollment simulation
vi.mock("@/components/voice/AudioRecorder", () => ({
  AudioRecorder: ({ onRecordingComplete, sampleLabel }: any) => (
    <div data-testid="mock-audio-recorder">
      <span>{sampleLabel}</span>
      <button
        onClick={() => {
          const fakeFile = new File(["fake-wav"], "sample.wav", { type: "audio/wav" });
          onRecordingComplete(fakeFile);
        }}
      >
        Simulate Re-enroll {sampleLabel}
      </button>
    </div>
  ),
}));

describe("Phase 8C - Voice Profile Management & Revocation Flow", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    useDemoStore.setState({ isDemoMode: false });
  });

  it("renders active profile details and cryptographic envelope information", async () => {
    (biometricsService.getProfile as any).mockResolvedValueOnce({
      id: "prof-uuid-9999",
      user_id: "user-1",
      status: "ACTIVE",
      sample_count: 3,
      mean_pairwise_similarity: 0.8872,
      model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
      created_at: "2026-11-13T10:00:00Z",
      updated_at: "2026-11-13T10:00:00Z",
      enrollment_records: [
        {
          duration_sec: 3.2,
          rms_energy: 0.09,
          peak_amplitude: 0.71,
          audio_format: "WAV",
          snr_db: 23.5,
        },
      ],
    });
    (consentService.getStatus as any).mockResolvedValueOnce({ has_active_consent: true });

    render(
      <QueryClientProvider client={queryClient}>
        <ProfilePage />
      </QueryClientProvider>
    );

    expect(await screen.findByText("prof-uuid-9999")).toBeInTheDocument();
    expect(screen.getByText(/3 speech recordings/i)).toBeInTheDocument();
    expect(screen.getByText(/0.8872/)).toBeInTheDocument();
    expect(screen.getByText(/AES-256-GCM Envelope V2/i)).toBeInTheDocument();
  });

  it("opens revocation modal, executes cryptographic shredding, and confirms success", async () => {
    (biometricsService.getProfile as any).mockResolvedValueOnce({
      id: "prof-uuid-9999",
      user_id: "user-1",
      status: "ACTIVE",
      sample_count: 3,
      mean_pairwise_similarity: 0.8872,
      model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
      created_at: "2026-11-13T10:00:00Z",
      updated_at: "2026-11-13T10:00:00Z",
      enrollment_records: [],
    });
    (consentService.getStatus as any).mockResolvedValueOnce({ has_active_consent: true });
    (biometricsService.revokeProfile as any).mockResolvedValueOnce({
      profile_id: "prof-uuid-9999",
      status: "REVOKED",
      message: "Voice profile permanently revoked and biometric vector shredded.",
    });

    render(
      <QueryClientProvider client={queryClient}>
        <ProfilePage />
      </QueryClientProvider>
    );

    const revokeBtn = await screen.findByRole("button", { name: /Revoke & Shred Voiceprint/i });
    fireEvent.click(revokeBtn);

    // Modal dialog pops up
    expect(
      screen.getByText(/Confirm Voice Profile Revocation & Shredding/i)
    ).toBeInTheDocument();

    const confirmBtn = screen.getByRole("button", { name: /Confirm Permanent Revocation/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(biometricsService.revokeProfile).toHaveBeenCalledTimes(1);
      expect(
        screen.getByText(/Voice profile permanently revoked and biometric vector shredded/i)
      ).toBeInTheDocument();
    });
  });

  it("handles re-enrollment modal with 3 recordings and invokes reEnrollVoice", async () => {
    (biometricsService.getProfile as any).mockResolvedValueOnce({
      id: "prof-uuid-9999",
      user_id: "user-1",
      status: "ACTIVE",
      sample_count: 3,
      mean_pairwise_similarity: 0.8872,
      model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
      created_at: "2026-11-13T10:00:00Z",
      updated_at: "2026-11-13T10:00:00Z",
      enrollment_records: [],
    });
    (consentService.getStatus as any).mockResolvedValueOnce({ has_active_consent: true });
    (biometricsService.reEnrollVoice as any).mockResolvedValueOnce({
      profile_id: "prof-uuid-NEW",
      previous_profile_id: "prof-uuid-9999",
      status: "ACTIVE",
      sample_count: 3,
      mean_pairwise_similarity: 0.901,
      message: "Voiceprint re-enrollment completed successfully.",
    });

    render(
      <QueryClientProvider client={queryClient}>
        <ProfilePage />
      </QueryClientProvider>
    );

    const reEnrollOpenBtn = await screen.findByRole("button", { name: /Re-enroll Voiceprint/i });
    fireEvent.click(reEnrollOpenBtn);

    expect(screen.getByText(/Re-enroll Reference Voiceprint/i)).toBeInTheDocument();

    const reRecordButtons = screen.getAllByText(/Simulate Re-enroll/i);
    expect(reRecordButtons).toHaveLength(3);

    fireEvent.click(reRecordButtons[0]);
    fireEvent.click(reRecordButtons[1]);
    fireEvent.click(reRecordButtons[2]);

    const submitBtn = screen.getByRole("button", { name: /Submit Re-enrollment/i });
    expect(submitBtn).toBeEnabled();
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(biometricsService.reEnrollVoice).toHaveBeenCalledTimes(1);
      expect(
        screen.getByText(/Voiceprint re-enrollment completed successfully/i)
      ).toBeInTheDocument();
    });
  });
});
