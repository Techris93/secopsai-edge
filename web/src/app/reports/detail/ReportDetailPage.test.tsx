import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterAll, afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ReportDetailPage from "./page";
import * as api from "@/lib/api";
import type { Report } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("id=report-alpha")
}));

vi.mock("@/lib/api", () => ({
  downloadReportHtml: vi.fn(),
  downloadReportPdf: vi.fn(),
  getReport: vi.fn()
}));

const report: Report = {
  id: "report-alpha",
  site_id: "site-alpha",
  title: "Weekly Edge Risk Summary",
  summary: "One new device and one risky service require review.",
  risk_level: "high",
  period_start: "2026-07-06T12:00:00Z",
  period_end: "2026-07-13T12:00:00Z",
  content: {
    provider: "openai",
    model: "gpt-test",
    recommended_actions: ["Confirm device ownership."],
    metrics: {
      assets_total: 14,
      assets_active: 13,
      new_devices: 1,
      risky_services: 1,
      wifi_security_findings: 0,
      open_findings: 2,
      acknowledged_findings: 1,
      resolved_findings: 3,
      scans_completed: 7,
      severity: { critical: 0, high: 1, medium: 1, low: 0, info: 0 }
    },
    findings: [
      {
        id: "finding-alpha",
        site_id: "site-alpha",
        asset_id: null,
        type: "risky_open_port",
        severity: "high",
        status: "open",
        title: "SSH exposed internally",
        summary: "A previously unseen service was observed.",
        evidence: {},
        mitre_attack: null,
        first_seen: "2026-07-12T12:00:00Z",
        last_seen: "2026-07-13T12:00:00Z",
        created_at: "2026-07-12T12:00:00Z",
        updated_at: "2026-07-13T12:00:00Z"
      }
    ]
  },
  created_at: "2026-07-13T12:00:00Z"
};

describe("ReportDetailPage exports", () => {
  const createObjectUrl = vi.fn(() => "blob:secopsai-report");
  const revokeObjectUrl = vi.fn();
  const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getReport).mockResolvedValue(report);
    vi.mocked(api.downloadReportPdf).mockResolvedValue(new Blob(["pdf"], { type: "application/pdf" }));
    vi.mocked(api.downloadReportHtml).mockResolvedValue(new Blob(["html"], { type: "text/html" }));
    class MockUrl extends URL {
      static createObjectURL = createObjectUrl;
      static revokeObjectURL = revokeObjectUrl;
    }
    vi.stubGlobal("URL", MockUrl);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  afterAll(() => {
    anchorClick.mockRestore();
  });

  it("downloads the authenticated PDF with a readable filename", async () => {
    render(React.createElement(ReportDetailPage));

    fireEvent.click(await screen.findByRole("button", { name: "Download PDF" }));

    await waitFor(() => expect(api.downloadReportPdf).toHaveBeenCalledWith("report-alpha"));
    expect(createObjectUrl).toHaveBeenCalledWith(expect.any(Blob));
    expect(anchorClick).toHaveBeenCalledOnce();
    expect(revokeObjectUrl).toHaveBeenCalledWith("blob:secopsai-report");
    expect(await screen.findByText("PDF report downloaded")).toBeInTheDocument();
  });

  it("keeps the HTML fallback and frozen executive metrics visible", async () => {
    render(React.createElement(ReportDetailPage));

    expect(await screen.findByText("Executive Metrics")).toBeInTheDocument();
    expect(screen.getByText("Scans completed")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Download HTML" }));
    await waitFor(() => expect(api.downloadReportHtml).toHaveBeenCalledWith("report-alpha"));
  });
});
