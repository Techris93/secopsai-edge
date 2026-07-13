import { expect, test } from "@playwright/test";
import { installEdgeApiMock, installOperatorSession } from "./mock-edge-api";

test.beforeEach(async ({ page }) => {
  await installOperatorSession(page);
});

test("pilot operator can queue a scan and triage a finding", async ({ page }) => {
  const api = await installEdgeApiMock(page);
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Wireless Intelligence & Asset Discovery" })).toBeVisible();
  await expect(page.getByText("Live API data")).toBeVisible();
  await page.getByLabel("Target CIDR").fill("192.168.50.0/24");
  await page.getByRole("button", { name: "Queue Remote Scan" }).click();
  await expect(page.getByText("Queued 192.168.50.0/24")).toBeVisible();
  expect(api.requests).toContainEqual({
    method: "POST",
    path: "/api/v1/scan-jobs",
    body: { target_cidr: "192.168.50.0/24", include_wifi: false }
  });

  await page.getByRole("link", { name: "Findings" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Findings", exact: true })).toBeVisible();
  await page.getByLabel("Select New device detected").check();
  await page.getByRole("button", { name: "Acknowledge" }).click();
  await expect(page.getByText("1 finding updated")).toBeVisible();
  expect(api.data.findings.find((finding) => finding.id === "finding-1")?.status).toBe("acknowledged");
});

test("pilot operator can create a recurring scan and generate a report", async ({ page }) => {
  const api = await installEdgeApiMock(page);
  await page.goto("/schedules");

  await expect(page.getByRole("heading", { name: "Scheduled Scans" })).toBeVisible();
  await page.getByRole("button", { name: "Create Schedule" }).click();
  await expect(page.getByText("Schedule created")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Daily network scan" })).toBeVisible();
  expect(api.data.schedules).toHaveLength(1);

  await page.getByRole("link", { name: "Reports" }).click();
  await page.getByRole("button", { name: "Generate" }).click();
  await expect(page.getByRole("heading", { name: "Browser-verified security report" })).toBeVisible();
  expect(api.requests.some((item) => item.method === "POST" && item.path === "/api/v1/reports/generate")).toBe(true);
});
