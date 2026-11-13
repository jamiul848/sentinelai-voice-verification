import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import EnrollmentPage from "@/app/(dashboard)/enrollment/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { consentService } from "@/lib/api/services/consent.service";
import { biometricsService } from "@/lib/api/services/biometrics.service";
import { useDemoStore } from "@/store/useDemoStore";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/enrollment",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api/services/consent.service", () => ({
  consentService: {
    getStatus: vi.fn(),
    grant: vi.fn(),
  },
}));

vi.mock("@/lib/api/services/biometrics.service", () => ({
  biometricsService: {
    getProfile: vi.fn(),
    enrollVoice: vi.fn(),
  },
}));

// Mock AudioRecorder to simulate capture easily in jsdom
vi.mock("@/components/voice/AudioRecorder", () => ({
  AudioRecorder: ({ onRecordingComplete, sampleLabel }: any) => (
    <div data-testid="mock-audio-recorder">
      <span>{sampleLabel}</span>
      <button
        onClick={() => {
          const fakeFile = new File(["fake-wav-data"], "test.wav", { type: "audio/wav" });
          onRecordingComplete(fakeFile);
        }}
      >
        Simulate Record {sampleLabel}
      </button>
    </div>
  ),
}));

describe("Phase 8C - Voice Enrollment Multi-Step Flow", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    useDemoStore.setState({ isDemoMode: false });
  });

  it("displays Step 1 consent disclosure if user does not have active consent", async () => {
    (consentService.getStatus as any).mockResolvedValueOnce({ has_active_consent: false });
    (biometricsService.getProfile as any).mockResolvedValueOnce(null);

    render(
      <QueryClientProvider client={queryClient}>
        <EnrollmentPage />
      </QueryClientProvider>
    );

    expect(await screen.findByText(/Biometric Processing Consent & Disclosure/i)).toBeInTheDocument();
    expect(screen.getByText(/Create your secure voice profile/i)).toBeInTheDocument();
  });

  it("advances to Step 2 when consent is already granted or newly authorized", async () => {
    (consentService.getStatus as any).mockResolvedValueOnce({ has_active_consent: true });
    (biometricsService.getProfile as any).mockResolvedValueOnce(null);

    render(
      <QueryClientProvider client={queryClient}>
        <EnrollmentPage />
      </QueryClientProvider>
    );

    expect(await screen.findByText(/Acoustic Protocol/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Utterance 1: Phonetic Baseline/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Utterance 2: Dynamic Inflection/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Utterance 3: Reference Anchor/i).length).toBeGreaterThan(0);
  });

  it("displays warning banner when user already has an active profile", async () => {
    (consentService.getStatus as any).mockResolvedValueOnce({ has_active_consent: true });
    (biometricsService.getProfile as any).mockResolvedValueOnce({
      id: "active-prof-uuid",
      user_id: "user-1",
      status: "ACTIVE",
      sample_count: 3,
      mean_pairwise_similarity: 0.88,
      model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
      created_at: "2026-11-13T10:00:00Z",
      updated_at: "2026-11-13T10:00:00Z",
    });

    render(
      <QueryClientProvider client={queryClient}>
        <EnrollmentPage />
      </QueryClientProvider>
    );

    expect(await screen.findByText(/You already have an active voice profile/i)).toBeInTheDocument();
    expect(screen.getByText(/Manage Profile/i)).toBeInTheDocument();
  });

  it("submits 3 samples and displays Step 4 confirmation on success", async () => {
    (consentService.getStatus as any).mockResolvedValueOnce({ has_active_consent: true });
    (biometricsService.getProfile as any).mockResolvedValueOnce(null);
    (biometricsService.enrollVoice as any).mockResolvedValueOnce({
      profile_id: "new-profile-uuid-1234",
      user_id: "user-1",
      status: "ACTIVE",
      sample_count: 3,
      mean_pairwise_similarity: 0.892,
      model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
      created_at: "2026-11-13T12:00:00Z",
    });

    render(
      <QueryClientProvider client={queryClient}>
        <EnrollmentPage />
      </QueryClientProvider>
    );

    // Wait for step 2 recording interface
    expect(await screen.findByText(/Acoustic Protocol/i)).toBeInTheDocument();

    const recordButtons = screen.getAllByText(/Simulate Record/i);
    expect(recordButtons).toHaveLength(3);

    // Simulate recording all 3 utterances
    fireEvent.click(recordButtons[0]);
    fireEvent.click(recordButtons[1]);
    fireEvent.click(recordButtons[2]);

    expect(screen.getByText(/3 of 3/i)).toBeInTheDocument();

    const enrollButton = screen.getByRole("button", { name: /Enroll Voiceprint/i });
    expect(enrollButton).toBeEnabled();

    fireEvent.click(enrollButton);

    // Wait for Step 4 success card
    await waitFor(() => {
      expect(screen.getByText(/Voiceprint Successfully Enrolled/i)).toBeInTheDocument();
    });

    expect(screen.getByText("new-profile-uuid-1234")).toBeInTheDocument();
    expect(screen.getByText(/Proceed to Voice Verification/i)).toBeInTheDocument();
  });
});
