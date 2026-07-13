import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, vi } from "vitest";
import * as api from "@/lib/api";
import { CoreIntegrationPanel } from "./CoreIntegrationPanel";

vi.mock("@/lib/api", () => ({
  apiBaseUrl: () => "https://edge.example.test",
  createIntegrationToken: vi.fn(),
  downloadCoreBundle: vi.fn(),
  fetchAuthIdentity: vi.fn().mockResolvedValue({
    subject: "owner@example.com",
    role: "owner",
    organization_id: "org-alpha",
    organizations: []
  }),
  listIntegrationTokens: vi.fn().mockResolvedValue([]),
  revokeIntegrationToken: vi.fn(),
  rotateIntegrationToken: vi.fn()
}));

beforeEach(() => {
  window.localStorage.clear();
  vi.clearAllMocks();
});
test("renders Core integration action buttons", async () => {
  render(React.createElement(CoreIntegrationPanel));
  await waitFor(() => expect(api.listIntegrationTokens).toHaveBeenCalled());

  expect(screen.getByText("SecOpsAI Core Integration")).toBeInTheDocument();
  const buttonText = screen.getAllByRole("button").map((button) => button.textContent);
  expect(buttonText).toEqual(expect.arrayContaining([
    expect.stringContaining("Download Bundle"),
    expect.stringContaining("Copy Export"),
    expect.stringContaining("Copy Import"),
    expect.stringContaining("Copy Assets"),
    expect.stringContaining("Copy Triage"),
    expect.stringContaining("Copy API Sync"),
    expect.stringContaining("Copy One-Step Sync"),
    expect.stringContaining("Copy Hosted Push"),
    expect.stringContaining("Install Auto Sync"),
    expect.stringContaining("Install Hosted Sync"),
    expect.stringContaining("Check Sync Status"),
    expect.stringContaining("Copy Support Bundle")
  ]));
  expect(screen.getByLabelText("Edge install path")).toHaveValue("$HOME/secopsai-edge");
  expect(screen.getByLabelText("Core API URL")).toHaveValue("https://secopsai-core-api.onrender.com");
  expect(screen.queryByDisplayValue(/chrixchange/)).not.toBeInTheDocument();
});

test("copies Core import command", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText }
  });

  render(React.createElement(CoreIntegrationPanel));
  fireEvent.click(screen.getByRole("button", { name: /Copy Import/ }));

  expect(writeText).toHaveBeenCalledWith(expect.stringContaining("secopsai.cli edge import"));
  expect(await screen.findByText("Copy Import copied")).toBeInTheDocument();
});

test("falls back when Core command clipboard permission is denied", async () => {
  const writeText = vi.fn().mockRejectedValue(new DOMException("Denied", "NotAllowedError"));
  const execCommand = vi.fn().mockReturnValue(true);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText }
  });
  Object.defineProperty(document, "execCommand", {
    configurable: true,
    value: execCommand
  });

  render(React.createElement(CoreIntegrationPanel));
  fireEvent.click(screen.getByRole("button", { name: /Copy Import/ }));

  expect(await screen.findByText("Copy Import copied")).toBeInTheDocument();
  expect(execCommand).toHaveBeenCalledWith("copy");
});

test("copies API sync with a silent scoped-token prompt", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText }
  });

  render(React.createElement(CoreIntegrationPanel));
  fireEvent.click(screen.getByRole("button", { name: /Copy API Sync/ }));

  await waitFor(() => expect(writeText).toHaveBeenCalled());
  const command = String(writeText.mock.calls[0][0]);
  expect(command).toContain("SECOPSAI_EDGE_ACCESS_TOKEN");
  expect(command).not.toContain("SECOPSAI_EDGE_ADMIN_TOKEN");
  expect(command).toContain("getpass.getpass");
});

test("updates copied commands from operator-configured install paths", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText }
  });
  render(React.createElement(CoreIntegrationPanel));

  fireEvent.change(screen.getByLabelText("Edge install path"), {
    target: { value: "/opt/secopsai-edge" }
  });
  fireEvent.click(screen.getByRole("button", { name: /Copy Edge Test/ }));

  await waitFor(() => expect(writeText).toHaveBeenCalledWith('cd "/opt/secopsai-edge"\n./scripts/edge test'));
  expect(window.localStorage.getItem("secopsai_edge_root")).toBe("/opt/secopsai-edge");
});

test("copies a hosted Core push without placing credentials in the command text", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText }
  });
  render(React.createElement(CoreIntegrationPanel));

  fireEvent.change(screen.getByLabelText("Core API URL"), {
    target: { value: "https://core.pilot.example" }
  });
  fireEvent.click(screen.getByRole("button", { name: /Copy Hosted Push/ }));

  await waitFor(() => expect(writeText).toHaveBeenCalled());
  const command = String(writeText.mock.calls[0][0]);
  expect(command).toContain("core push --cloud");
  expect(command).toContain("https://core.pilot.example");
  expect(command).toContain("SECOPSAI_EDGE_CORE_TOKEN");
  expect(command).toContain("SECOPSAI_CORE_INGEST_TOKEN");
  expect(command).toContain("getpass.getpass");
  expect(command).not.toContain("hosted-core-ingest-secret");
  expect(window.localStorage.getItem("secopsai_core_api_url")).toBe(
    "https://core.pilot.example"
  );
});

test("creates scoped workspace tokens and offers revocation", async () => {
  const created = {
    id: "token-alpha",
    organization_id: "org-alpha",
    name: "SecOpsAI Core sync",
    scopes: ["core:export"],
    state: "active",
    expires_at: "2026-10-01T00:00:00Z",
    expires_in_days: 90,
    rotation_recommended: false,
    created_at: "2026-07-01T00:00:00Z",
    access_token: "secopsai_integration_one-time-secret"
  };
  vi.mocked(api.createIntegrationToken).mockResolvedValue(created);
  vi.mocked(api.revokeIntegrationToken).mockResolvedValue({
    ...created,
    state: "revoked",
    revoked_at: "2026-07-02T00:00:00Z"
  });

  render(React.createElement(CoreIntegrationPanel));
  fireEvent.click(await screen.findByRole("button", { name: "Create Core token" }));

  expect(await screen.findByText("secopsai_integration_one-time-secret")).toBeInTheDocument();
  expect(api.createIntegrationToken).toHaveBeenCalledWith("SecOpsAI Core sync", ["core:export"]);
  fireEvent.click(screen.getByRole("button", { name: "Revoke SecOpsAI Core sync (token-al)" }));
  await waitFor(() => expect(api.revokeIntegrationToken).toHaveBeenCalledWith("token-alpha"));
  expect(await screen.findByText("Integration token revoked")).toBeInTheDocument();
});

test("creates a read-only operator dashboard token", async () => {
  vi.mocked(api.createIntegrationToken).mockResolvedValue({
    id: "token-operations",
    organization_id: "org-alpha",
    name: "SecOpsAI operator dashboard",
    scopes: ["operations:read"],
    state: "active",
    expires_at: "2026-10-01T00:00:00Z",
    expires_in_days: 90,
    rotation_recommended: false,
    created_at: "2026-07-01T00:00:00Z",
    access_token: "secopsai_integration_operations-secret"
  });

  render(React.createElement(CoreIntegrationPanel));
  fireEvent.click(await screen.findByRole("button", { name: "Create dashboard token" }));

  expect(await screen.findByText("secopsai_integration_operations-secret")).toBeInTheDocument();
  expect(api.createIntegrationToken).toHaveBeenCalledWith(
    "SecOpsAI operator dashboard",
    ["operations:read"]
  );
});

test("warns about expiry and creates an overlapping replacement", async () => {
  const expiring = {
    id: "token-expiring",
    organization_id: "org-alpha",
    name: "SecOpsAI operator dashboard",
    scopes: ["operations:read"],
    state: "active",
    expires_at: "2026-07-20T00:00:00Z",
    expires_in_days: 7,
    rotation_recommended: true,
    created_at: "2026-04-20T00:00:00Z"
  };
  vi.mocked(api.listIntegrationTokens).mockResolvedValue([expiring]);
  vi.mocked(api.rotateIntegrationToken).mockResolvedValue({
    ...expiring,
    id: "token-replacement",
    expires_at: "2026-10-11T00:00:00Z",
    expires_in_days: 90,
    rotation_recommended: false,
    access_token: "secopsai_integration_replacement-secret"
  });

  render(React.createElement(CoreIntegrationPanel));

  expect(await screen.findByText("Rotation recommended")).toBeInTheDocument();
  expect(screen.getByText(/7 days left/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Rotate SecOpsAI operator dashboard (token-ex)" }));

  await waitFor(() => expect(api.rotateIntegrationToken).toHaveBeenCalledWith("token-expiring"));
  expect(await screen.findByText("secopsai_integration_replacement-secret")).toBeInTheDocument();
  expect(screen.getByText(/Update the downstream service/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Revoke SecOpsAI operator dashboard (token-re)" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Revoke SecOpsAI operator dashboard (token-ex)" })).toBeInTheDocument();
});
