import type { Page, Route } from "@playwright/test";
import { sampleData } from "../src/lib/sample-data";
import type { DashboardData, Report, ScanJob, ScanSchedule } from "../src/lib/types";

const API_PATTERN = "http://127.0.0.1:8000/api/v1/**";

export type MockEdgeApi = {
  data: DashboardData;
  requests: Array<{ method: string; path: string; body: unknown }>;
  requireMfa: boolean;
  dashboardFailure: { status: number; detail: string } | null;
  systemHealth: "ready" | "degraded";
};

export async function installOperatorSession(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.sessionStorage.setItem("secopsai_dashboard_session", "browser-e2e-session");
  });
}

export async function installEdgeApiMock(page: Page): Promise<MockEdgeApi> {
  const state: MockEdgeApi = {
    data: structuredClone(sampleData),
    requests: [],
    requireMfa: false,
    dashboardFailure: null,
    systemHealth: "ready"
  };

  state.data.onboarding = {
    api_connected: true,
    sites_created: state.data.onboarding?.sites_created ?? true,
    sensor_registered: state.data.onboarding?.sensor_registered ?? true,
    worker_online: true,
    first_scan_completed: true,
    first_report_generated: state.data.onboarding?.first_report_generated ?? true,
    schedule_configured: state.data.onboarding?.schedule_configured ?? false,
    notifications_configured: state.data.onboarding?.notifications_configured ?? false
  };
  state.data.sensors[0] = {
    ...state.data.sensors[0],
    status: "online",
    connection_state: "online",
    last_seen_at: new Date().toISOString()
  };

  await page.route(API_PATTERN, async (route) => handleRoute(route, state));
  return state;
}

async function handleRoute(route: Route, state: MockEdgeApi): Promise<void> {
  const request = route.request();
  const url = new URL(request.url());
  const method = request.method();
  const body = request.postDataJSON?.() ?? null;
  state.requests.push({ method, path: `${url.pathname}${url.search}`, body });

  if (method === "POST" && url.pathname === "/api/v1/auth/login") {
    if (state.requireMfa) {
      return json(route, {
        access_token: null,
        token_type: "bearer",
        expires_in: 300,
        user: { ...operatorUser(), mfa_enabled: true },
        mfa_required: true,
        mfa_challenge: "browser-e2e-mfa-challenge"
      });
    }
    return json(route, {
      access_token: "browser-e2e-session",
      token_type: "bearer",
      expires_in: 28_800,
      user: operatorUser()
    });
  }
  if (method === "POST" && url.pathname === "/api/v1/auth/password-reset/request") {
    return json(route, { status: "accepted" }, 202);
  }
  if (method === "POST" && url.pathname === "/api/v1/auth/password-reset/confirm") {
    return json(route, { status: "password_reset" });
  }
  if (method === "POST" && url.pathname === "/api/v1/user-invitations/accept") {
    return json(route, { status: "invitation_accepted" });
  }
  if (method === "POST" && url.pathname === "/api/v1/auth/mfa/verify") {
    return json(route, {
      access_token: "browser-e2e-session",
      token_type: "bearer",
      expires_in: 28_800,
      user: { ...operatorUser(), mfa_enabled: true }
    });
  }
  if (method === "GET" && url.pathname === "/api/v1/auth/me") {
    return json(route, {
      subject: "operator@example.com",
      role: "owner",
      organization_id: "organization-demo",
      organizations: [
        {
          id: "organization-demo",
          name: "Demo Workspace",
          slug: "demo-workspace",
          active: true,
          role: "owner",
          created_at: new Date().toISOString()
        }
      ],
      user: operatorUser()
    });
  }

  const collection = collectionForPath(url.pathname, state.data);
  if (method === "GET" && collection !== undefined) {
    if (state.dashboardFailure) {
      return json(route, { detail: state.dashboardFailure.detail }, state.dashboardFailure.status);
    }
    return json(route, collection);
  }

  if (method === "GET" && url.pathname === "/api/v1/audit-logs") return json(route, []);

  if (method === "GET" && url.pathname === "/api/v1/system/status") {
    return json(route, {
      status: state.systemHealth,
      environment: "test",
      version: "0.3.3",
      commit: "browser-e2e",
      schema_revision: "0016_wifi_provenance",
      expected_schema_revision: "0016_wifi_provenance",
      ai_provider: "mock",
      organization_id: "organization-demo",
      server_time: new Date().toISOString()
    });
  }
  if (method === "GET" && url.pathname === "/api/v1/users") return json(route, [operatorUser()]);
  if (method === "GET" && url.pathname === "/api/v1/user-invitations") return json(route, []);
  if (method === "GET" && url.pathname === "/api/v1/account-access/deliveries") return json(route, []);
  if (method === "GET" && url.pathname === "/api/v1/integration-tokens") return json(route, []);
  if (method === "GET" && url.pathname === "/api/v1/notification-deliveries") return json(route, []);
  if (method === "GET" && url.pathname === "/api/v1/data-lifecycle") {
    return json(route, {
      organization_id: "organization-demo",
      observation_days: 90,
      scan_history_days: 180,
      notification_delivery_days: 90,
      account_access_days: 30,
      credential_history_days: 90,
      report_days: 365,
      audit_log_days: 365,
      last_run_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
  }
  if (method === "PATCH" && url.pathname === "/api/v1/data-lifecycle") {
    return json(route, {
      organization_id: "organization-demo",
      ...(body as Record<string, number>),
      last_run_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
  }
  if (method === "POST" && url.pathname === "/api/v1/data-lifecycle/run-now") {
    return json(route, {
      organizations: 1,
      skipped: 0,
      deleted: { asset_observations: 2, scan_jobs: 1 },
      run_at: new Date().toISOString()
    });
  }

  const siteExportMatch = url.pathname.match(/^\/api\/v1\/sites\/([^/]+)\/export$/);
  if (method === "GET" && siteExportMatch) {
    const site = state.data.sites.find((item) => item.id === siteExportMatch[1]);
    if (!site) return json(route, { detail: "Site not found" }, 404);
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: { "Content-Disposition": `attachment; filename="${site.name.toLowerCase().replaceAll(" ", "-")}-export.json"` },
      body: JSON.stringify({ schema_version: "secopsai.edge.site-export.v1", site })
    });
  }
  const siteMatch = url.pathname.match(/^\/api\/v1\/sites\/([^/]+)$/);
  if (method === "DELETE" && siteMatch) {
    const index = state.data.sites.findIndex((item) => item.id === siteMatch[1]);
    if (index < 0) return json(route, { detail: "Site not found" }, 404);
    state.data.sites.splice(index, 1);
    return json(route, {
      status: "deleted",
      site_id: siteMatch[1],
      deleted: { sites: 1 }
    });
  }

  if (method === "POST" && url.pathname === "/api/v1/scan-jobs") {
    const payload = body as { target_cidr: string; include_wifi: boolean };
    const job: ScanJob = {
      id: `job-${state.data.scanJobs.length + 1}`,
      site_id: "site-demo",
      sensor_id: "sensor-demo",
      target_cidr: payload.target_cidr,
      include_wifi: payload.include_wifi,
      status: "queued",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      preview: {},
      result_summary: {}
    };
    state.data.scanJobs.unshift(job);
    return json(route, job, 201);
  }
  if (method === "POST" && url.pathname === "/api/v1/reports/generate") {
    const report: Report = {
      ...state.data.reports[0],
      id: `report-${state.data.reports.length + 1}`,
      title: "Browser-verified security report",
      created_at: new Date().toISOString()
    };
    state.data.reports.unshift(report);
    return json(route, report, 201);
  }
  const reportMatch = url.pathname.match(/^\/api\/v1\/reports\/([^/]+)$/);
  if (method === "GET" && reportMatch) {
    const report = state.data.reports.find((item) => item.id === reportMatch[1]);
    return report ? json(route, report) : json(route, { detail: "Report not found" }, 404);
  }
  const reportExportMatch = url.pathname.match(/^\/api\/v1\/reports\/([^/]+)\/export\.(pdf|html)$/);
  if (method === "GET" && reportExportMatch) {
    const [, reportId, format] = reportExportMatch;
    const report = state.data.reports.find((item) => item.id === reportId);
    if (!report) return json(route, { detail: "Report not found" }, 404);
    const contentType = format === "pdf" ? "application/pdf" : "text/html; charset=utf-8";
    const body = format === "pdf" ? "%PDF-1.4\n% SecOpsAI browser fixture\n%%EOF\n" : `<h1>${report.title}</h1>`;
    return route.fulfill({ status: 200, contentType, body });
  }
  if (method === "POST" && url.pathname === "/api/v1/sensor-enrollments") {
    const payload = body as { site_id: string; label: string };
    const site = state.data.sites.find((item) => item.id === payload.site_id);
    if (!site) return json(route, { detail: "Site not found" }, 404);
    const enrollment = {
      id: `enrollment-${state.data.sensorEnrollments.length + 1}`,
      organization_id: site.organization_id ?? "organization-demo",
      site_id: site.id,
      site_name: site.name,
      label: payload.label,
      state: "active" as const,
      enrollment_token: "secopsai_enroll.browser-one-time-token-with-safe-length",
      expires_at: new Date(Date.now() + 30 * 60_000).toISOString(),
      created_at: new Date().toISOString()
    };
    state.data.sensorEnrollments.unshift(enrollment);
    return json(route, enrollment, 201);
  }
  const enrollmentMatch = url.pathname.match(/^\/api\/v1\/sensor-enrollments\/([^/]+)$/);
  if (method === "DELETE" && enrollmentMatch) {
    const enrollment = state.data.sensorEnrollments.find((item) => item.id === enrollmentMatch[1]);
    if (!enrollment) return json(route, { detail: "Enrollment not found" }, 404);
    enrollment.state = "revoked";
    enrollment.revoked_at = new Date().toISOString();
    return json(route, enrollment);
  }
  if (method === "POST" && url.pathname === "/api/v1/scan-schedules") {
    const payload = body as Omit<ScanSchedule, "id" | "created_at" | "updated_at">;
    const schedule: ScanSchedule = {
      ...payload,
      id: `schedule-${state.data.schedules.length + 1}`,
      site_id: payload.site_id || "site-demo",
      sensor_id: payload.sensor_id || "sensor-demo",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    state.data.schedules.unshift(schedule);
    return json(route, schedule, 201);
  }
  if (method === "POST" && url.pathname === "/api/v1/scan-schedules/run-due") {
    return json(route, { queued: 1, job_ids: ["job-scheduled"] });
  }
  const findingStatusMatch = url.pathname.match(/^\/api\/v1\/findings\/([^/]+)\/status$/);
  if (method === "POST" && findingStatusMatch) {
    const finding = state.data.findings.find((item) => item.id === findingStatusMatch[1]);
    if (!finding) return json(route, { detail: "Finding not found" }, 404);
    finding.status = url.searchParams.get("status_value") ?? finding.status;
    finding.updated_at = new Date().toISOString();
    return json(route, finding);
  }

  return json(route, { detail: `Unhandled browser test route: ${method} ${url.pathname}` }, 404);
}

function collectionForPath(path: string, data: DashboardData): unknown | undefined {
  const collections: Record<string, unknown> = {
    "/api/v1/sites": data.sites,
    "/api/v1/assets": data.assets,
    "/api/v1/wifi-networks": data.wifiNetworks,
    "/api/v1/baselines": data.baselines,
    "/api/v1/findings": data.findings,
    "/api/v1/reports": data.reports,
    "/api/v1/scan-jobs": data.scanJobs,
    "/api/v1/sensors": data.sensors,
    "/api/v1/sensor-enrollments": data.sensorEnrollments,
    "/api/v1/scan-schedules": data.schedules,
    "/api/v1/notification-endpoints": data.notifications,
    "/api/v1/onboarding/status": data.onboarding
  };
  return collections[path];
}

function operatorUser() {
  return {
    id: "operator-user",
    email: "operator@example.com",
    role: "owner",
    active: true,
    mfa_enabled: false,
    created_at: new Date().toISOString()
  };
}

async function json(route: Route, body: unknown, status = 200): Promise<void> {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body)
  });
}
