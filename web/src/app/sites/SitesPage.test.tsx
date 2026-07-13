import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import SitesPage from "./page";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  apiBaseUrl: vi.fn(() => "https://edge.example.test"),
  createSite: vi.fn(),
  createSensorEnrollment: vi.fn(),
  deleteSite: vi.fn(),
  disableSensor: vi.fn(),
  downloadSiteExport: vi.fn(),
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
    const command = screen.getByText(/bootstrap-secopsai-edge\.sh/);
    expect(command).toHaveTextContent("gh release download");
    expect(command).toHaveTextContent("curl -fsSLO");
    expect(command).toHaveTextContent("--enrollment-token");
    expect(screen.getByText(/Private pilots need GitHub CLI access/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy install command" })).toBeInTheDocument();
  });

  it("gates permanent site deletion behind explicit owner proof", async () => {
    vi.mocked(api.deleteSite).mockResolvedValue({ status: "deleted", site_id: "site-alpha", deleted: {} });
    render(React.createElement(SitesPage));

    fireEvent.click(await screen.findByRole("button", { name: "Delete" }));
    const deleteButton = screen.getByRole("button", { name: "Delete site permanently" });
    expect(deleteButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Type Alpha Office"), { target: { value: "Alpha Office" } });
    fireEvent.change(screen.getByLabelText("Current password"), { target: { value: "owner-password" } });
    fireEvent.click(screen.getByLabelText(/I understand this action is permanent/));
    expect(deleteButton).toBeEnabled();
    fireEvent.click(deleteButton);

    await waitFor(() => expect(api.deleteSite).toHaveBeenCalledWith("site-alpha", {
      confirmation: "Alpha Office",
      current_password: "owner-password",
      code: undefined,
      acknowledge_permanent: true
    }));
  });
});
