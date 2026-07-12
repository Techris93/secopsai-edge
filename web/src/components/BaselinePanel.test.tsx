import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { BaselinePanel } from "./BaselinePanel";

const baseline = {
  id: "baseline-1",
  site_id: "site-1",
  kind: "service",
  status: "active",
  matcher: { asset_id: "asset-1", port: 22, protocol: "tcp" },
  finding_types: ["risky_open_port"],
  reason: "Approved administration service",
  created_by: "operator",
  expires_at: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
};

vi.mock("@/lib/api", () => ({
  fetchBaselines: vi.fn(async () => [baseline]),
  disableBaseline: vi.fn(async () => ({ ...baseline, status: "disabled" }))
}));

test("lists and disables an approved baseline", async () => {
  const api = await import("@/lib/api");
  render(React.createElement(BaselinePanel));

  expect(await screen.findByText("Approved administration service")).toBeInTheDocument();
  expect(screen.getByText("Risky Open Port")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Disable" }));

  await waitFor(() => expect(api.disableBaseline).toHaveBeenCalledWith("baseline-1"));
  expect(await screen.findByText(/Findings acknowledged only by this rule were reopened/)).toBeInTheDocument();
});
