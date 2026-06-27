import { sampleData } from "./sample-data";
import type { Asset, DashboardData, Finding, Report, ScanJob, Sensor, WifiNetwork } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const SESSION_TOKEN_KEY = "secopsai_dashboard_session";

type ApiResult<T> = {
  data: T;
  live: boolean;
  error?: string;
};

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
    throw new Error(`${response.status} ${response.statusText}`);
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

export async function loginDashboard(adminToken: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ admin_token: adminToken }),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  const payload = (await response.json()) as { access_token: string };
  window.sessionStorage.setItem(SESSION_TOKEN_KEY, payload.access_token);
}

export function apiBaseUrl(): string {
  return API_BASE_URL;
}

export async function fetchDashboardData(): Promise<ApiResult<DashboardData>> {
  try {
    const [assets, wifiNetworks, findings, reports, scanJobs, sensors] = await Promise.all([
      requestJson<Asset[]>("/api/v1/assets"),
      requestJson<WifiNetwork[]>("/api/v1/wifi-networks"),
      requestJson<Finding[]>("/api/v1/findings"),
      requestJson<Report[]>("/api/v1/reports"),
      requestJson<ScanJob[]>("/api/v1/scan-jobs"),
      requestJson<Sensor[]>("/api/v1/sensors")
    ]);
    return { data: { assets, wifiNetworks, findings, reports, scanJobs, sensors }, live: true };
  } catch (error) {
    return {
      data: sampleData,
      live: false,
      error: error instanceof Error ? error.message : "API unavailable"
    };
  }
}

export async function generateReport(): Promise<Report> {
  return requestJson<Report>("/api/v1/reports/generate", { method: "POST" });
}

export async function createScanJob(targetCidr: string, includeWifi: boolean): Promise<ScanJob> {
  return requestJson<ScanJob>("/api/v1/scan-jobs", {
    method: "POST",
    body: JSON.stringify({ target_cidr: targetCidr, include_wifi: includeWifi })
  });
}

export async function cancelScanJob(jobId: string): Promise<ScanJob> {
  return requestJson<ScanJob>(`/api/v1/scan-jobs/${jobId}/cancel`, { method: "POST" });
}

export async function retryScanJob(jobId: string): Promise<ScanJob> {
  return requestJson<ScanJob>(`/api/v1/scan-jobs/${jobId}/retry`, { method: "POST" });
}

export async function updateFindingStatus(findingId: string, status: string): Promise<Finding> {
  return requestJson<Finding>(
    `/api/v1/findings/${findingId}/status?status_value=${encodeURIComponent(status)}`,
    { method: "POST" }
  );
}
