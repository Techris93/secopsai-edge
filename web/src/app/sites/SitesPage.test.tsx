import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import SitesPage from "./page";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  apiBaseUrl: vi.fn(() => "https://edge.example.test"),
  createSite: vi.fn(),
  createSensorEnrollment: vi.fn(),
  disableSensor: vi.fn(),
  enableSensor: vi.fn(),
  fetchDashboardData: vi.fn(),
  revokeSensorEnrollment: vi.fn(),
  rotateSensorToken: vi.fn(),
  updateSensor: vi.fn(),
  updateSite: vi.fn()
}));

const now = "2026-07-13T00:00:00Z";

describe("SitesPage sensor enrollment", () => {
  beforeEach(() => {
    vi.mocked(api.fetchDashboardData).mockResolvedValue({
      live: true,
      mode: "live",
      data: {
        sites: [{ id: "site-alpha", organization_id: "org-alpha", name: "Alpha Office", created_at: now }],
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
    vi.mocked(api.createSensorEnrollment).mockResolvedValue({
      id: "enrollment-alpha",
      organization_id: "org-alpha",
      site_id: "site-alpha",
      site_name: "Alpha Office",
      label: "Alpha Office sensor",
      state: "active",
      expires_at: "2026-07-13T00:30:00Z",
      created_at: now,
      enrollment_token: "single-use-enrollment-token-value-123456"
    });
  });

  it("creates a one-time token and renders the exact installer command", async () => {
    render(React.createElement(SitesPage));

    const button = await screen.findByRole("button", { name: "Enroll sensor" });
    fireEvent.click(button);

    await waitFor(() => expect(api.createSensorEnrollment).toHaveBeenCalledWith("site-alpha", "Alpha Office sensor"));
    expect(screen.getByText("One-time installer")).toBeInTheDocument();
    expect(screen.getByText(/bootstrap-secopsai-edge\.sh/)).toHaveTextContent("--enrollment-token");
    expect(screen.getByRole("button", { name: "Copy install command" })).toBeInTheDocument();
  });
});
