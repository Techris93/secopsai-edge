import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { installEdgeApiMock, installOperatorSession } from "./mock-edge-api";

const principalRoutes = [
  "/",
  "/onboarding",
  "/sites",
  "/assets",
  "/wifi",
  "/findings",
  "/schedules",
  "/reports",
  "/audit",
  "/settings"
];

test.beforeEach(async ({ page }) => {
  await installOperatorSession(page);
});

test("principal operator routes pass automated WCAG A/AA checks", async ({ page }) => {
  await installEdgeApiMock(page);

  for (const route of principalRoutes) {
    await page.goto(route);
    await expect(page.locator("main h1").first()).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(results.violations, `${route}: ${formatViolations(results.violations)}`).toEqual([]);
  }
});

test("sensor enrollment is one-time, copyable, dismissible, and revocable", async ({ page, context }) => {
  const api = await installEdgeApiMock(page);
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto("/sites");

  await page.getByRole("button", { name: "Enroll sensor" }).click();
  await expect(page.getByText("One-time installer")).toBeVisible();
  await expect(page.getByText(/secopsai_enroll\.browser-one-time-token/)).toBeVisible();
  await page.getByRole("button", { name: "Copy install command" }).click();
  await expect(page.getByRole("button", { name: "Copied" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toContain("bootstrap-secopsai-edge.sh");

  await page.getByRole("button", { name: "Dismiss enrollment secret" }).click();
  await expect(page.getByText("One-time installer")).toBeHidden();
  await expect(page.getByText("Pending enrollment")).toBeVisible();
  await page.getByRole("button", { name: "Revoke" }).click();
  await expect(page.getByText("Sensor enrollment revoked")).toBeVisible();
  expect(api.requests.some((item) => item.method === "POST" && item.path === "/api/v1/sensor-enrollments")).toBe(true);
  expect(api.requests.some((item) => item.method === "DELETE" && item.path.startsWith("/api/v1/sensor-enrollments/"))).toBe(true);
});

test("authenticated report PDF downloads with a readable filename", async ({ page }) => {
  const api = await installEdgeApiMock(page);
  await page.goto("/reports/detail?id=report-1");
  await expect(page.getByRole("heading", { level: 1, name: "SecOpsAI Edge Weekly Security Summary", exact: true })).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download PDF" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("secopsai-edge-weekly-security-summary.pdf");
  await expect(page.getByText("PDF report downloaded")).toBeVisible();
  expect(api.requests.some((item) => item.method === "GET" && item.path === "/api/v1/reports/report-1/export.pdf")).toBe(true);
});

test("keyboard users can skip navigation and identify the current page", async ({ page }) => {
  await installEdgeApiMock(page);
  await page.goto("/findings");

  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
  await expect(page.getByRole("link", { name: "Findings", exact: true }).first()).toHaveAttribute("aria-current", "page");
});

test("empty, unavailable, and degraded states are explicit", async ({ page }) => {
  const api = await installEdgeApiMock(page);
  api.data.assets = [];
  await page.goto("/assets");
  await expect(page.getByText("No assets match the current filters. Run an authorized scan or clear the filters.")).toBeVisible();

  api.dashboardFailure = { status: 503, detail: "Pilot API temporarily unavailable" };
  await page.goto("/findings");
  await expect(page.getByRole("heading", { name: "API session required" })).toBeVisible();
  await expect(page.getByRole("paragraph").filter({ hasText: "Pilot API temporarily unavailable" })).toBeVisible();

  api.dashboardFailure = null;
  api.systemHealth = "degraded";
  await page.goto("/settings");
  await expect(page.getByText("Deployment needs attention")).toBeVisible();
});

test("principal routes do not overflow the viewport", async ({ page }) => {
  await installEdgeApiMock(page);
  for (const route of principalRoutes) {
    await page.goto(route);
    await expect(page.locator("main h1").first()).toBeVisible();
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      page: document.documentElement.scrollWidth
    }));
    expect(dimensions.page, `${route} has horizontal overflow`).toBeLessThanOrEqual(dimensions.viewport);
  }
});

function formatViolations(violations: Array<{ id: string; nodes: Array<{ target: unknown }> }>): string {
  return violations
    .map((violation) => `${violation.id}: ${violation.nodes.map((node) => JSON.stringify(node.target)).join(", ")}`)
    .join(" | ");
}
