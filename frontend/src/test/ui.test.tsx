import React from "react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatDateTime, formatLatency, formatScore, truncateId } from "@/lib/utils";

describe("UI Primitives & Utility Helpers", () => {
  it("renders Button with children and handles loading state", () => {
    const { rerender } = render(<Button>Execute Verification</Button>);
    expect(screen.getByText("Execute Verification")).toBeInTheDocument();

    rerender(<Button isLoading>Execute Verification</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("renders Badge variants correctly", () => {
    render(<Badge variant="success">MATCH</Badge>);
    expect(screen.getByText("MATCH")).toBeInTheDocument();
  });

  it("renders Card layout components", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Biometric Profile</CardTitle>
        </CardHeader>
        <CardContent>Profile Active</CardContent>
      </Card>
    );
    expect(screen.getByText("Biometric Profile")).toBeInTheDocument();
    expect(screen.getByText("Profile Active")).toBeInTheDocument();
  });

  it("renders Input with error state", () => {
    render(<Input placeholder="Email" error="Invalid email address" />);
    expect(screen.getByPlaceholderText("Email")).toBeInTheDocument();
    expect(screen.getByText("Invalid email address")).toBeInTheDocument();
  });

  it("formats decimal scores accurately", () => {
    expect(formatScore(0.887451, 4)).toBe("0.8875");
    expect(formatScore(0.405898, 6)).toBe("0.405898");
  });

  it("formats millisecond latencies", () => {
    expect(formatLatency(480)).toBe("480 ms");
    expect(formatLatency(1240.5)).toBe("1.24 s");
  });

  it("truncates long identifiers cleanly", () => {
    const id = "77a80b12-9c31-4e78-8380-49658ec3429a";
    expect(truncateId(id, 8, 6)).toBe("77a80b12...c3429a");
  });

  it("formats ISO timestamps", () => {
    const iso = "2026-11-13T08:46:07Z";
    const formatted = formatDateTime(iso);
    expect(formatted).toContain("2026");
  });
});
