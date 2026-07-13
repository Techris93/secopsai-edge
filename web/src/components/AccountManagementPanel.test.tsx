import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { AccountManagementPanel } from "./AccountManagementPanel";

const admin = {
  id: "user-1",
  email: "admin@example.com",
  role: "admin",
  active: true,
  created_at: new Date().toISOString(),
  last_login_at: null,
  password_changed_at: null,
  mfa_enabled: false
};

const failedDelivery = {
  id: "delivery-1",
  user_id: admin.id,
  email: admin.email,
  purpose: "password_reset",
  status: "failed",
  attempts: 4,
  max_attempts: 4,
  expires_at: new Date(Date.now() + 60_000).toISOString(),
  next_attempt_at: new Date().toISOString(),
  detail: "SMTP unavailable",
  created_at: new Date().toISOString()
};

vi.mock("@/lib/api", () => ({
  fetchAuthIdentity: vi.fn(async () => ({ subject: admin.email, role: admin.role, user: admin })),
  listUsers: vi.fn(async () => [admin]),
  listUserInvitations: vi.fn(async () => []),
  listAccountAccessDeliveries: vi.fn(async () => [failedDelivery]),
  retryAccountAccessDelivery: vi.fn(async () => ({ ...failedDelivery, status: "delivered", attempts: 1 })),
  createUserInvitation: vi.fn(async (payload) => ({ id: "invitation-1", user_id: "user-2", organization_id: "organization-1", state: "pending", delivery_status: "queued", expires_at: new Date().toISOString(), created_at: new Date().toISOString(), ...payload })),
  revokeUserInvitation: vi.fn(async () => undefined),
  updateUser: vi.fn(async (_id, payload) => ({ ...admin, ...payload })),
  resetUserMfa: vi.fn(async () => undefined),
  changeDashboardPassword: vi.fn(async () => undefined),
  beginDashboardMfa: vi.fn(async () => ({ secret: "MFASECRET", provisioning_uri: "otpauth://totp/test", expires_at: new Date().toISOString() })),
  enableDashboardMfa: vi.fn(async () => ["ABCDE-FGHIJ"]),
  regenerateDashboardMfaRecoveryCodes: vi.fn(async () => ["KLMNO-PQRST"]),
  disableDashboardMfa: vi.fn(async () => undefined)
}));

test("invites a pilot user and exposes session-revoking controls", async () => {
  const api = await import("@/lib/api");
  render(React.createElement(AccountManagementPanel));

  expect((await screen.findAllByText("admin@example.com")).length).toBeGreaterThan(0);
  fireEvent.change(screen.getByPlaceholderText("user@example.com"), { target: { value: "viewer@example.com" } });
  fireEvent.click(screen.getByRole("button", { name: "Invite" }));

  await waitFor(() => expect(api.createUserInvitation).toHaveBeenCalledWith({
    email: "viewer@example.com",
    role: "viewer"
  }));
  expect(await screen.findByText(/Invitation queued/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Disable" }));
  await waitFor(() => expect(api.updateUser).toHaveBeenCalledWith("user-1", { active: false }));

  expect(screen.getByText("SMTP unavailable")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await waitFor(() => expect(api.retryAccountAccessDelivery).toHaveBeenCalledWith("delivery-1"));
});

test("lets an owner reset another operator's MFA", async () => {
  const api = await import("@/lib/api");
  const owner = { ...admin, id: "owner-1", email: "owner@example.com", role: "owner" };
  const target = { ...admin, id: "target-1", email: "target@example.com", mfa_enabled: true };
  vi.mocked(api.fetchAuthIdentity).mockResolvedValue({
    subject: owner.email,
    role: owner.role,
    organization_id: "organization-1",
    organizations: [],
    user: owner
  });
  vi.mocked(api.listUsers).mockResolvedValue([owner, target]);
  vi.spyOn(window, "confirm").mockReturnValue(true);

  render(React.createElement(AccountManagementPanel));
  expect(await screen.findByText("target@example.com")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Reset MFA" }));

  await waitFor(() => expect(api.resetUserMfa).toHaveBeenCalledWith("target-1"));
  expect(await screen.findByText(/MFA reset for target@example.com/)).toBeInTheDocument();
});
