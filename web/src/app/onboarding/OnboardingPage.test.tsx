import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OnboardingPage from "./page";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchDashboardData: vi.fn()
}));

describe("OnboardingPage worker commands", () => {
  beforeEach(() => {
    vi.mocked(api.fetchDashboardData).mockResolvedValue({
      live: true,
      mode: "live",
      data: {
        sites: [],
        assets: [],
        wifiNetworks: [],
        baselines: [],
        findings: [],
        reports: [],
        scanJobs: [],
        sensors: [],
        sensorEnrollments: [],
        schedules: [],
        notifications: [],
        onboarding: null
      }
    });
  });

  it("exposes a copyable worker uninstall command", async () => {
    render(React.createElement(OnboardingPage));

    const button = await screen.findByRole("button", { name: /Copy Worker Uninstall/ });
    expect(button).toBeInTheDocument();
    expect(screen.getByText(/worker uninstall/)).toBeInTheDocument();
  });
});
