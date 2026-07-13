import { sampleData } from "./sample-data";
import type {
  Asset,
  AssetDetail,
  AuthIdentity,
  AuditLog,
  BaselineRule,
  DashboardData,
  Finding,
  FindingDetail,
  FindingNote,
  NotificationEndpoint,
  Organization,
  OnboardingStatus,
  Report,
  ScanJob,
  ScanSchedule,
  Sensor,
  Site,
  User,
  WifiNetwork
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const SESSION_TOKEN_KEY = "secopsai_dashboard_session";
const DEMO_FALLBACK_ENABLED = process.env.NEXT_PUBLIC_SECOPSAI_DEMO_MODE === "true";

export type DashboardDataMode = "live" | "demo" | "blocked";

export type ApiResult<T> = {
  data: T | null;
  live: boolean;
  mode: DashboardDataMode;
  error?: string;
};

async function responseError(response: Response): Promise<Error> {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) return new Error(payload.detail);
  } catch {
    // Non-JSON responses fall back to the HTTP status below.
  }
  return new Error(`${response.status} ${response.statusText}`);
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const sessionToken = getDashboardSessionToken();
  if (!sessionToken) {
    throw new Error("Dashboard session required");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${sessionToken}`,
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });
  if (!response.ok) {
    throw await responseError(response);
  }
  return response.json() as Promise<T>;
}

function getDashboardSessionToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(SESSION_TOKEN_KEY);
}

export function hasDashboardSession(): boolean {
  return Boolean(getDashboardSessionToken());
}

export function clearDashboardSession(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(SESSION_TOKEN_KEY);
}

export async function logoutDashboard(): Promise<void> {
  await requestJson<{ status: string }>("/api/v1/auth/logout", { method: "POST" });
  clearDashboardSession();
}

export async function changeDashboardPassword(currentPassword: string, newPassword: string): Promise<void> {
  await requestJson<{ status: string }>("/api/v1/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
  });
  clearDashboardSession();
}

export async function listUsers(): Promise<User[]> {
  return requestJson<User[]>("/api/v1/users");
}

export async function createUser(payload: { email: string; password: string; role: string }): Promise<User> {
  return requestJson<User>("/api/v1/users", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateUser(
  userId: string,
  payload: Partial<{ role: string; active: boolean; password: string }>
): Promise<User> {
  return requestJson<User>(`/api/v1/users/${userId}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export async function loginDashboard(adminToken: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ admin_token: adminToken }),
    cache: "no-store"
  });

  if (!response.ok) {
    throw await responseError(response);
  }

  const payload = (await response.json()) as { access_token: string };
  window.sessionStorage.setItem(SESSION_TOKEN_KEY, payload.access_token);
}

export async function loginDashboardUser(email: string, password: string): Promise<User | null> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    cache: "no-store"
  });

  if (!response.ok) {
    throw await responseError(response);
  }

  const payload = (await response.json()) as { access_token: string; user?: User | null };
  window.sessionStorage.setItem(SESSION_TOKEN_KEY, payload.access_token);
  return payload.user ?? null;
}

export async function fetchAuthIdentity(): Promise<AuthIdentity> {
  return requestJson<AuthIdentity>("/api/v1/auth/me");
}

export async function switchWorkspace(organizationId: string): Promise<void> {
  const payload = await requestJson<{ access_token: string }>("/api/v1/auth/workspace", {
    method: "POST",
    body: JSON.stringify({ organization_id: organizationId })
  });
  window.sessionStorage.setItem(SESSION_TOKEN_KEY, payload.access_token);
}

export async function createOrganization(name: string): Promise<Organization> {
  return requestJson<Organization>("/api/v1/organizations", {
    method: "POST",
    body: JSON.stringify({ name })
  });
}

export function apiBaseUrl(): string {
  return API_BASE_URL;
}

export async function fetchDashboardData(): Promise<ApiResult<DashboardData>> {
  try {
    const [sites, assets, wifiNetworks, baselines, findings, reports, scanJobs, sensors, schedules, notifications, onboarding] =
      await Promise.all([
        requestJson<Site[]>("/api/v1/sites"),
        requestJson<Asset[]>("/api/v1/assets"),
        requestJson<WifiNetwork[]>("/api/v1/wifi-networks"),
        requestJson<BaselineRule[]>("/api/v1/baselines"),
        requestJson<Finding[]>("/api/v1/findings"),
        requestJson<Report[]>("/api/v1/reports"),
        requestJson<ScanJob[]>("/api/v1/scan-jobs"),
        requestJson<Sensor[]>("/api/v1/sensors"),
        requestJson<ScanSchedule[]>("/api/v1/scan-schedules"),
        requestJson<NotificationEndpoint[]>("/api/v1/notification-endpoints"),
        requestJson<OnboardingStatus>("/api/v1/onboarding/status")
      ]);
    return {
      data: { sites, assets, wifiNetworks, baselines, findings, reports, scanJobs, sensors, schedules, notifications, onboarding },
      live: true,
      mode: "live"
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "API unavailable";
    if (DEMO_FALLBACK_ENABLED) {
      return {
        data: sampleData,
        live: false,
        mode: "demo",
        error: message
      };
    }

    return {
      data: null,
      live: false,
      mode: "blocked",
      error: message
    };
  }
}

export async function generateReport(): Promise<Report> {
  return requestJson<Report>("/api/v1/reports/generate", { method: "POST" });
}

export async function generateSiteReport(siteId?: string): Promise<Report> {
  const suffix = siteId ? `?site_id=${encodeURIComponent(siteId)}` : "";
  return requestJson<Report>(`/api/v1/reports/generate${suffix}`, { method: "POST" });
}

export async function getReport(reportId: string): Promise<Report> {
  return requestJson<Report>(`/api/v1/reports/${reportId}`);
}

export async function downloadReportHtml(reportId: string): Promise<Blob> {
  const sessionToken = getDashboardSessionToken();
  if (!sessionToken) {
    throw new Error("Dashboard session required");
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/reports/${reportId}/export.html`, {
    headers: {
      Authorization: `Bearer ${sessionToken}`
    },
    cache: "no-store"
  });
  if (!response.ok) {
    throw await responseError(response);
  }
  return response.blob();
}

export async function downloadCoreBundle(): Promise<Blob> {
  const sessionToken = getDashboardSessionToken();
  if (!sessionToken) {
    throw new Error("Dashboard session required");
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/core/export`, {
    headers: {
      Authorization: `Bearer ${sessionToken}`
    },
    cache: "no-store"
  });
  if (!response.ok) {
    throw await responseError(response);
  }
  return response.blob();
}

export async function createScanJob(targetCidr: string, includeWifi: boolean): Promise<ScanJob> {
  return requestJson<ScanJob>("/api/v1/scan-jobs", {
    method: "POST",
    body: JSON.stringify({ target_cidr: targetCidr, include_wifi: includeWifi })
  });
}

export async function createSite(name: string): Promise<Site> {
  return requestJson<Site>("/api/v1/sites", {
    method: "POST",
    body: JSON.stringify({ name })
  });
}

export async function updateSite(siteId: string, name: string): Promise<Site> {
  return requestJson<Site>(`/api/v1/sites/${siteId}`, {
    method: "PATCH",
    body: JSON.stringify({ name })
  });
}

export async function createScanSchedule(payload: {
  name: string;
  site_id?: string;
  sensor_id?: string;
  target_cidr: string;
  frequency: string;
  time_of_day: string;
  timezone: string;
  day_of_week?: number | null;
  include_wifi: boolean;
  enabled: boolean;
}): Promise<ScanSchedule> {
  return requestJson<ScanSchedule>("/api/v1/scan-schedules", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateScanSchedule(
  scheduleId: string,
  payload: Partial<{
    name: string;
    target_cidr: string;
    frequency: string;
    time_of_day: string;
    timezone: string;
    day_of_week: number | null;
    include_wifi: boolean;
    enabled: boolean;
    sensor_id: string;
  }>
): Promise<ScanSchedule> {
  return requestJson<ScanSchedule>(`/api/v1/scan-schedules/${scheduleId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteScanSchedule(scheduleId: string): Promise<void> {
  await requestJson<{ status: string }>(`/api/v1/scan-schedules/${scheduleId}`, { method: "DELETE" });
}

export async function runDueSchedules(): Promise<{ queued: number; job_ids: string[] }> {
  return requestJson<{ queued: number; job_ids: string[] }>("/api/v1/scan-schedules/run-due", { method: "POST" });
}

export async function cancelScanJob(jobId: string): Promise<ScanJob> {
  return requestJson<ScanJob>(`/api/v1/scan-jobs/${jobId}/cancel`, { method: "POST" });
}

export async function retryScanJob(jobId: string): Promise<ScanJob> {
  return requestJson<ScanJob>(`/api/v1/scan-jobs/${jobId}/retry`, { method: "POST" });
}

export async function getAsset(assetId: string): Promise<AssetDetail> {
  return requestJson<AssetDetail>(`/api/v1/assets/${assetId}`);
}

export async function fetchBaselines(): Promise<BaselineRule[]> {
  return requestJson<BaselineRule[]>("/api/v1/baselines");
}

export async function createAssetBaseline(assetId: string, reason: string): Promise<BaselineRule> {
  return requestJson<BaselineRule>(`/api/v1/assets/${assetId}/baseline`, {
    method: "POST",
    body: JSON.stringify({ reason })
  });
}

export async function createServiceBaseline(serviceId: string, reason: string): Promise<BaselineRule> {
  return requestJson<BaselineRule>(`/api/v1/services/${serviceId}/baseline`, {
    method: "POST",
    body: JSON.stringify({ reason })
  });
}

export async function createWifiBaseline(wifiId: string, reason: string): Promise<BaselineRule> {
  return requestJson<BaselineRule>(`/api/v1/wifi-networks/${wifiId}/baseline`, {
    method: "POST",
    body: JSON.stringify({ reason })
  });
}

export async function disableBaseline(baselineId: string): Promise<BaselineRule> {
  return requestJson<BaselineRule>(`/api/v1/baselines/${baselineId}`, { method: "DELETE" });
}

export async function fetchAuditLogs(filters?: {
  action?: string;
  resourceType?: string;
  sensorId?: string;
  limit?: number;
}): Promise<AuditLog[]> {
  const params = new URLSearchParams();
  if (filters?.action) params.set("action", filters.action);
  if (filters?.resourceType) params.set("resource_type", filters.resourceType);
  if (filters?.sensorId) params.set("sensor_id", filters.sensorId);
  params.set("limit", String(filters?.limit ?? 100));
  return requestJson<AuditLog[]>(`/api/v1/audit-logs?${params.toString()}`);
}

export async function updateFindingStatus(findingId: string, status: string): Promise<Finding> {
  return requestJson<Finding>(
    `/api/v1/findings/${findingId}/status?status_value=${encodeURIComponent(status)}`,
    { method: "POST" }
  );
}

export async function getFinding(findingId: string): Promise<FindingDetail> {
  return requestJson<FindingDetail>(`/api/v1/findings/${findingId}`);
}

export async function createFindingNote(findingId: string, body: string, author = "operator"): Promise<FindingNote> {
  return requestJson<FindingNote>(`/api/v1/findings/${findingId}/notes`, {
    method: "POST",
    body: JSON.stringify({ body, author })
  });
}

export async function verifyFinding(findingId: string): Promise<ScanJob> {
  return requestJson<ScanJob>(`/api/v1/findings/${findingId}/verify`, { method: "POST" });
}

export async function updateSensor(sensorId: string, payload: { name?: string; hostname?: string }): Promise<Sensor> {
  return requestJson<Sensor>(`/api/v1/sensors/${sensorId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function rotateSensorToken(sensorId: string): Promise<{ sensor_id: string; sensor_token: string }> {
  return requestJson<{ sensor_id: string; sensor_token: string }>(`/api/v1/sensors/${sensorId}/rotate-token`, {
    method: "POST"
  });
}

export async function disableSensor(sensorId: string): Promise<Sensor> {
  return requestJson<Sensor>(`/api/v1/sensors/${sensorId}/disable`, { method: "POST" });
}

export async function enableSensor(sensorId: string): Promise<Sensor> {
  return requestJson<Sensor>(`/api/v1/sensors/${sensorId}/enable`, { method: "POST" });
}

export async function createNotificationEndpoint(payload: {
  name: string;
  type: string;
  target: string;
  site_id?: string;
  events: string[];
  enabled: boolean;
}): Promise<NotificationEndpoint> {
  return requestJson<NotificationEndpoint>("/api/v1/notification-endpoints", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateNotificationEndpoint(
  endpointId: string,
  payload: Partial<{ name: string; target: string; events: string[]; enabled: boolean }>
): Promise<NotificationEndpoint> {
  return requestJson<NotificationEndpoint>(`/api/v1/notification-endpoints/${endpointId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteNotificationEndpoint(endpointId: string): Promise<void> {
  await requestJson<{ status: string }>(`/api/v1/notification-endpoints/${endpointId}`, { method: "DELETE" });
}

export async function testNotificationEndpoint(endpointId: string): Promise<{ ok: boolean; detail: string }> {
  return requestJson<{ ok: boolean; detail: string }>(`/api/v1/notification-endpoints/${endpointId}/test`, {
    method: "POST"
  });
}

export async function listNotificationDeliveries(limit = 50): Promise<import("@/lib/types").NotificationDelivery[]> {
  return requestJson<import("@/lib/types").NotificationDelivery[]>(`/api/v1/notification-deliveries?limit=${limit}`);
}

export async function retryNotificationDelivery(deliveryId: string): Promise<import("@/lib/types").NotificationDelivery> {
  return requestJson<import("@/lib/types").NotificationDelivery>(`/api/v1/notification-deliveries/${deliveryId}/retry`, {
    method: "POST"
  });
}
