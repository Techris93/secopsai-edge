import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { NotificationPanel } from "./NotificationPanel";

const delivery = {
  id: "delivery-1",
  endpoint_id: "endpoint-1",
  event_type: "high_finding",
  status: "failed",
  attempts: 4,
  max_attempts: 4,
  next_attempt_at: new Date().toISOString(),
  response_detail: "Webhook returned HTTP 503",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
};

vi.mock("@/lib/api", () => ({
  fetchDashboardData: vi.fn(async () => ({
    mode: "live",
    data: { sites: [], notifications: [] }
  })),
  listNotificationDeliveries: vi.fn(async () => [delivery]),
  retryNotificationDelivery: vi.fn(async () => ({ ...delivery, status: "delivered", attempts: 1 })),
  createNotificationEndpoint: vi.fn(),
  deleteNotificationEndpoint: vi.fn(),
  testNotificationEndpoint: vi.fn(),
  updateNotificationEndpoint: vi.fn()
}));

test("shows failed notification delivery and retries it", async () => {
  const api = await import("@/lib/api");
  render(React.createElement(NotificationPanel));

  expect(await screen.findByText("Webhook returned HTTP 503")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));

  await waitFor(() => expect(api.retryNotificationDelivery).toHaveBeenCalledWith("delivery-1"));
  expect(await screen.findByText("Delivery delivered")).toBeInTheDocument();
});
