import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DataLifecyclePanel } from "./DataLifecyclePanel";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchDataLifecyclePolicy: vi.fn(),
  runDataLifecycle: vi.fn(),
  updateDataLifecyclePolicy: vi.fn()
}));

const policy = {
  organization_id: "org-alpha",
  observation_days: 90,
  scan_history_days: 180,
  notification_delivery_days: 90,
  account_access_days: 30,
  credential_history_days: 90,
  report_days: 365,
  audit_log_days: 365,
  last_run_at: null,
  created_at: "2026-07-13T00:00:00Z",
  updated_at: "2026-07-13T00:00:00Z"
};

describe("DataLifecyclePanel", () => {
  beforeEach(() => {
    vi.mocked(api.fetchDataLifecyclePolicy).mockResolvedValue(policy);
    vi.mocked(api.updateDataLifecyclePolicy).mockResolvedValue(policy);
    vi.mocked(api.runDataLifecycle).mockResolvedValue({
      organizations: 1,
      skipped: 0,
      deleted: { asset_observations: 3 },
      run_at: "2026-07-13T00:00:00Z"
    });
  });

  it("updates retention and runs cleanup with visible evidence", async () => {
    render(React.createElement(DataLifecyclePanel));
    const observations = await screen.findByLabelText("Asset observations retention days");
    fireEvent.change(observations, { target: { value: "120" } });
    fireEvent.click(screen.getByRole("button", { name: "Save policy" }));
    await waitFor(() => expect(api.updateDataLifecyclePolicy).toHaveBeenCalledWith(
      expect.objectContaining({ observation_days: 120 })
    ));

    fireEvent.click(screen.getByRole("button", { name: "Run cleanup" }));
    await waitFor(() => expect(api.runDataLifecycle).toHaveBeenCalled());
    expect(await screen.findByText(/Cleanup complete: 3 expired records removed/)).toBeInTheDocument();
  });
});
