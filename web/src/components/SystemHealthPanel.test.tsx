import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SystemHealthPanel } from "./SystemHealthPanel";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchSystemStatus: vi.fn(async () => ({
    status: "ready",
    environment: "pilot",
    version: "0.2.9",
    commit: "abc123def456789",
    schema_revision: "0013_account_recovery",
    expected_schema_revision: "0013_account_recovery",
    ai_provider: "mock",
    organization_id: "org-alpha",
    server_time: "2026-07-13T00:00:00Z"
  }))
}));

describe("SystemHealthPanel", () => {
  it("shows safe build and schema state and supports refresh", async () => {
    render(React.createElement(SystemHealthPanel));

    expect(await screen.findByText("API and database ready")).toBeInTheDocument();
    expect(screen.getByText("0013_account_recovery (current)")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => expect(api.fetchSystemStatus).toHaveBeenCalledTimes(2));
  });
});
