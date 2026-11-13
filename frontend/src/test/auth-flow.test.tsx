import { describe, expect, it } from "vitest";
import { useAuthStore } from "@/store/useAuthStore";
import { useDemoStore } from "@/store/useDemoStore";
import { DEMO_PROFILE, DEMO_USER, DEMO_VERIFICATION_HISTORY } from "@/config/demo";

describe("State Management & Session Stores", () => {
  it("initializes and mutates useAuthStore correctly", () => {
    const store = useAuthStore.getState();

    // Set authentication session
    store.setAuth(DEMO_USER, "mock-jwt-access-token", "mock-jwt-refresh-token");

    const activeState = useAuthStore.getState();
    expect(activeState.isAuthenticated).toBe(true);
    expect(activeState.user?.email).toBe("sarah.connor@sentinelvoice.io");
    expect(activeState.accessToken).toBe("mock-jwt-access-token");

    // Clear authentication session
    activeState.clearAuth();
    const loggedOutState = useAuthStore.getState();
    expect(loggedOutState.isAuthenticated).toBe(false);
    expect(loggedOutState.user).toBeNull();
    expect(loggedOutState.accessToken).toBeNull();
  });

  it("toggles and isolates demo mode without data leakage", () => {
    const demo = useDemoStore.getState();
    expect(demo.isDemoMode).toBe(false);

    demo.toggleDemoMode();
    expect(useDemoStore.getState().isDemoMode).toBe(true);

    demo.setDemoMode(false);
    expect(useDemoStore.getState().isDemoMode).toBe(false);
  });

  it("preserves demo datasets integrity", () => {
    expect(DEMO_PROFILE.sample_count).toBe(3);
    expect(DEMO_PROFILE.mean_pairwise_similarity).toBeGreaterThan(0.7);
    expect(DEMO_VERIFICATION_HISTORY.length).toBeGreaterThan(0);
    expect(DEMO_VERIFICATION_HISTORY[0].decision).toBe("MATCH");
    expect(DEMO_VERIFICATION_HISTORY[1].decision).toBe("NO_MATCH");
  });
});

