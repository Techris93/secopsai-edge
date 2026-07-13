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
  password_changed_at: null
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
  listAccountAccessDeliveries: vi.fn(async () => [failedDelivery]),
  retryAccountAccessDelivery: vi.fn(async () => ({ ...failedDelivery, status: "delivered", attempts: 1 })),
  createUser: vi.fn(async (payload) => ({ ...admin, id: "user-2", ...payload })),
  updateUser: vi.fn(async (_id, payload) => ({ ...admin, ...payload })),
  changeDashboardPassword: vi.fn(async () => undefined)
}));

test("creates a pilot user and exposes session-revoking controls", async () => {
  const api = await import("@/lib/api");
  render(React.createElement(AccountManagementPanel));

  expect((await screen.findAllByText("admin@example.com")).length).toBeGreaterThan(0);
  fireEvent.change(screen.getByPlaceholderText("user@example.com"), { target: { value: "viewer@example.com" } });
  fireEvent.change(screen.getByPlaceholderText("Temporary password"), { target: { value: "temporary-password" } });
  fireEvent.click(screen.getByRole("button", { name: "Add user" }));

  await waitFor(() => expect(api.createUser).toHaveBeenCalledWith({
    email: "viewer@example.com",
    password: "temporary-password",
    role: "viewer"
  }));
  expect(await screen.findByText(/Share the temporary password through a secure channel/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Disable" }));
  await waitFor(() => expect(api.updateUser).toHaveBeenCalledWith("user-1", { active: false }));

  expect(screen.getByText("SMTP unavailable")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await waitFor(() => expect(api.retryAccountAccessDelivery).toHaveBeenCalledWith("delivery-1"));
});
