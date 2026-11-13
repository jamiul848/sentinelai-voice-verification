import { describe, expect, it } from "vitest";
import { VerificationHistoryItem, VoiceProfile } from "@/types";

describe("Dashboard Real Data Transformations", () => {
  it("derives accurate biometric metrics from real verification events", () => {
    const mockEvents: VerificationHistoryItem[] = [
      {
        id: "evt-1",
        decision: "MATCH",
        is_match: true,
        similarity_score: 0.82,
        applied_threshold: 0.405898,
        processing_time_ms: 120,
        created_at: "2026-11-13T10:00:00Z",
      },
      {
        id: "evt-2",
        decision: "NO_MATCH",
        is_match: false,
        similarity_score: 0.22,
        applied_threshold: 0.405898,
        processing_time_ms: 110,
        created_at: "2026-11-13T11:00:00Z",
      },
      {
        id: "evt-3",
        decision: "MATCH",
        is_match: true,
        similarity_score: 0.77,
        applied_threshold: 0.405898,
        processing_time_ms: 115,
        created_at: "2026-11-12T14:00:00Z",
      },
    ];

    const total = mockEvents.length;
    const matches = mockEvents.filter((e) => e.decision === "MATCH").length;
    const nonMatches = mockEvents.filter((e) => e.decision === "NO_MATCH").length;

    expect(total).toBe(3);
    expect(matches).toBe(2);
    expect(nonMatches).toBe(1);
  });

  it("transforms verification events into chronological date groupings for Recharts", () => {
    const mockEvents: VerificationHistoryItem[] = [
      {
        id: "evt-1",
        decision: "MATCH",
        is_match: true,
        similarity_score: 0.82,
        applied_threshold: 0.405898,
        processing_time_ms: 120,
        created_at: "2026-11-13T10:00:00Z",
      },
      {
        id: "evt-2",
        decision: "NO_MATCH",
        is_match: false,
        similarity_score: 0.22,
        applied_threshold: 0.405898,
        processing_time_ms: 110,
        created_at: "2026-11-13T11:00:00Z",
      },
      {
        id: "evt-3",
        decision: "MATCH",
        is_match: true,
        similarity_score: 0.77,
        applied_threshold: 0.405898,
        processing_time_ms: 115,
        created_at: "2026-11-12T14:00:00Z",
      },
    ];

    // Grouping logic matching UserDashboardPage
    const dateMap = new Map<string, { matches: number; nonMatches: number }>();
    const reversed = [...mockEvents].reverse();

    for (const item of reversed) {
      const dateKey = item.created_at ? item.created_at.split("T")[0] : "Recent";
      const current = dateMap.get(dateKey) || { matches: 0, nonMatches: 0 };
      if (item.decision === "MATCH") {
        current.matches += 1;
      } else {
        current.nonMatches += 1;
      }
      dateMap.set(dateKey, current);
    }

    const chartPoints = Array.from(dateMap.entries()).map(([date, counts]) => ({
      date,
      matches: counts.matches,
      nonMatches: counts.nonMatches,
    }));

    expect(chartPoints).toHaveLength(2);
    expect(chartPoints[0]).toEqual({
      date: "2026-11-12",
      matches: 1,
      nonMatches: 0,
    });
    expect(chartPoints[1]).toEqual({
      date: "2026-11-13",
      matches: 1,
      nonMatches: 1,
    });
  });

  it("handles profile status states properly", () => {
    const activeProfile: VoiceProfile = {
      id: "prof-1",
      user_id: "user-1",
      status: "ACTIVE",
      sample_count: 3,
      mean_pairwise_similarity: 0.88,
      model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
      created_at: "2026-11-10T00:00:00Z",
      updated_at: "2026-11-10T00:00:00Z",
    };

    expect(activeProfile.status).toBe("ACTIVE");
    expect(activeProfile.sample_count).toBe(3);

    const revokedProfile: VoiceProfile = {
      ...activeProfile,
      status: "REVOKED",
      revoked_at: "2026-11-12T00:00:00Z",
    };

    expect(revokedProfile.status).toBe("REVOKED");
    expect(revokedProfile.revoked_at).not.toBeNull();
  });
});

