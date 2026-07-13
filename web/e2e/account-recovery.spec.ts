import { expect, test } from "@playwright/test";
import { installEdgeApiMock } from "./mock-edge-api";

test("operator can request and complete a non-enumerating password reset", async ({ page }) => {
  const api = await installEdgeApiMock(page);
  const resetToken = "secopsai_access.browser-test-token-with-safe-length";

  await page.goto(`/settings#reset_token=${resetToken}`);
  await expect(page.getByText("Complete password reset")).toBeVisible();
  await expect(page).toHaveURL(/\/settings$/);

  await page.getByPlaceholder("New password (12+ characters)").fill("new-browser-password");
  await page.getByPlaceholder("Confirm new password").fill("new-browser-password");
  await page.getByRole("button", { name: "Reset password" }).click();
  await expect(page.getByRole("status")).toContainText("Password reset complete");

  const confirm = api.requests.find((item) => item.path === "/api/v1/auth/password-reset/confirm");
  expect(confirm?.body).toEqual({ token: resetToken, new_password: "new-browser-password" });

  await page.getByPlaceholder("admin@example.com").fill("unknown@example.com");
  await page.getByRole("button", { name: "Send password reset" }).click();
  await expect(page.getByRole("status")).toContainText("If the account exists");
});

test("operator can establish a dashboard session with email and password", async ({ page }) => {
  await installEdgeApiMock(page);
  await page.goto("/settings");

  await page.getByPlaceholder("admin@example.com").fill("operator@example.com");
  await page.getByPlaceholder("Password").fill("operator-password");
  await page.getByRole("button", { name: "Connect", exact: true }).click();

  await expect(page.getByText("Connected as operator@example.com")).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Connected. Refresh dashboard pages");
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("secopsai_dashboard_session"))).toBe(
    "browser-e2e-session"
  );
});

test("invited operator can accept a one-time workspace invitation", async ({ page }) => {
  const api = await installEdgeApiMock(page);
  const invitationToken = "secopsai_access.browser-invitation-token-with-safe-length";

  await page.goto(`/settings#invitation_token=${invitationToken}`);
  await expect(page.getByText("Accept workspace invitation")).toBeVisible();
  await expect(page).toHaveURL(/\/settings$/);
  await page.getByPlaceholder("Account password (12+ characters)").fill("invited-browser-password");
  await page.getByPlaceholder("Confirm account password").fill("invited-browser-password");
  await page.getByRole("button", { name: "Accept invitation" }).click();
  await expect(page.getByRole("status")).toContainText("Invitation accepted");

  const acceptance = api.requests.find((item) => item.path === "/api/v1/user-invitations/accept");
  expect(acceptance?.body).toEqual({ token: invitationToken, password: "invited-browser-password" });
});

test("operator can complete an MFA login challenge", async ({ page }) => {
  const api = await installEdgeApiMock(page);
  api.requireMfa = true;
  await page.goto("/settings");

  await page.getByPlaceholder("admin@example.com").fill("operator@example.com");
  await page.getByPlaceholder("Password").fill("operator-password");
  await page.getByRole("button", { name: "Connect", exact: true }).click();
  await expect(page.getByText("Verify multi-factor authentication")).toBeVisible();
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("secopsai_dashboard_session"))).toBeNull();

  await page.getByPlaceholder("6-digit code or recovery code").fill("123456");
  await page.getByRole("button", { name: "Verify", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Multi-factor authentication verified");
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("secopsai_dashboard_session"))).toBe(
    "browser-e2e-session"
  );
});
