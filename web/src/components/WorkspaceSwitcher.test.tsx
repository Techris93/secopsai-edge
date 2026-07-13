import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

vi.mock("@/lib/api", () => ({
  fetchAuthIdentity: vi.fn(async () => ({
    subject: "owner@example.com",
    role: "owner",
    organization_id: "org-alpha",
    organizations: [
      { id: "org-alpha", name: "Alpha", slug: "alpha", active: true, role: "owner", created_at: "2026-01-01T00:00:00Z" },
      { id: "org-bravo", name: "Bravo", slug: "bravo", active: true, role: "viewer", created_at: "2026-01-01T00:00:00Z" }
    ]
  })),
  createOrganization: vi.fn(),
  switchWorkspace: vi.fn()
}));

describe("WorkspaceSwitcher", () => {
  it("shows the active workspace, accessible alternatives, and owner action", async () => {
    render(React.createElement(WorkspaceSwitcher));

    await waitFor(() => expect(screen.getByLabelText("Active workspace")).toHaveValue("org-alpha"));
    expect(screen.getByRole("option", { name: "Bravo" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create workspace" })).toBeInTheDocument();
    expect(screen.getByText("owner")).toBeInTheDocument();
  });
});
