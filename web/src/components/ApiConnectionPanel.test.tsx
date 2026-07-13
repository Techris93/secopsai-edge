import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { ApiConnectionPanel } from "./ApiConnectionPanel";

vi.mock("@/lib/api", () => ({
  apiBaseUrl: () => "https://edge-api.example.test",
  clearDashboardSession: vi.fn(),
  fetchAuthIdentity: vi.fn(),
  hasDashboardSession: vi.fn(() => false),
  loginDashboard: vi.fn(async () => undefined),
  loginDashboardUser: vi.fn(async () => ({ email: "admin@example.com" })),
  logoutDashboard: vi.fn(async () => undefined)
}));

test("prefers dashboard user login over admin token", async () => {
  const api = await import("@/lib/api");
  render(React.createElement(ApiConnectionPanel));

  expect(screen.getByText("API Connection")).toBeInTheDocument();
  expect(screen.getByPlaceholderText("admin@example.com")).toBeInTheDocument();
  expect(screen.getByText("Legacy admin token recovery")).toBeInTheDocument();

  fireEvent.change(screen.getByPlaceholderText("admin@example.com"), {
    target: { value: "admin@example.com" }
  });
  fireEvent.change(screen.getByPlaceholderText("Password"), {
    target: { value: "correct horse battery staple" }
  });
  fireEvent.click(screen.getByRole("button", { name: "Connect" }));

  await waitFor(() => expect(api.loginDashboardUser).toHaveBeenCalledWith("admin@example.com", "correct horse battery staple"));
  expect(await screen.findByText(/Connected. Refresh dashboard pages/)).toBeInTheDocument();
});

test("keeps legacy admin token as recovery flow", async () => {
  const api = await import("@/lib/api");
  render(React.createElement(ApiConnectionPanel));

  fireEvent.click(screen.getByText("Legacy admin token recovery"));
  fireEvent.change(screen.getByPlaceholderText("Enter API admin token"), {
    target: { value: "dev-admin-token" }
  });
  fireEvent.click(screen.getByRole("button", { name: "Connect Token" }));

  await waitFor(() => expect(api.loginDashboard).toHaveBeenCalledWith("dev-admin-token"));
  expect(await screen.findByText("Connected with legacy admin token session.")).toBeInTheDocument();
});
