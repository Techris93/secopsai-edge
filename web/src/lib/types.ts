export type Severity = "critical" | "high" | "medium" | "low";

export type Asset = {
  id: string;
  site_id: string;
  ip_address: string;
  mac_address?: string | null;
  vendor?: string | null;
  hostname?: string | null;
  os_guess?: string | null;
  device_type?: string | null;
  status: string;
  first_seen_at: string;
  last_seen_at: string;
  services?: Array<{
    id: string;
    port: number;
    protocol: string;
    name?: string | null;
    product?: string | null;
    version?: string | null;
    state: string;
    first_seen_at: string;
    last_seen_at: string;
  }>;
};

export type AssetObservation = {
  id: string;
  site_id: string;
  sensor_id: string;
  scan_id: string;
  asset_id: string;
  ip_address: string;
  mac_address?: string | null;
  vendor?: string | null;
  hostname?: string | null;
  os_guess?: string | null;
  raw_source?: string | null;
  observed_at: string;
};

export type AssetTimelineEvent = {
  id: string;
  kind: string;
  title: string;
  summary: string;
  occurred_at: string;
  severity: Severity | "info" | string;
  metadata: Record<string, unknown>;
};

export type AssetDetail = {
  asset: Asset;
  observations: AssetObservation[];
  findings: Finding[];
  timeline: AssetTimelineEvent[];
};

export type WifiNetwork = {
  id: string;
  site_id: string;
  ssid: string;
  bssid?: string | null;
  channel?: number | null;
  signal?: number | null;
  encryption?: string | null;
  status: string;
  first_seen_at: string;
  last_seen_at: string;
};

export type BaselineRule = {
  id: string;
  site_id: string;
  kind: "asset" | "service" | "wifi" | string;
  status: "active" | "disabled" | string;
  matcher: Record<string, string | number | null>;
  finding_types: string[];
  reason?: string | null;
  created_by: string;
  expires_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type AuditLog = {
  id: string;
  user_id?: string | null;
  sensor_id?: string | null;
  action: string;
  resource_type?: string | null;
  resource_id?: string | null;
  details: Record<string, unknown>;
  created_at: string;
};

export type Finding = {
  id: string;
  site_id: string;
  asset_id?: string | null;
  wifi_network_id?: string | null;
  type: string;
  severity: Severity;
  status: string;
  title: string;
  summary: string;
  evidence: Record<string, unknown>;
  mitre_attack: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
};

export type FindingNote = {
  id: string;
  finding_id: string;
  author: string;
  body: string;
  created_at: string;
};

export type FindingDetail = Finding & {
  notes: FindingNote[];
};

export type Report = {
  id: string;
  site_id: string;
  title: string;
  summary: string;
  risk_level: Severity;
  content: {
    findings?: Finding[];
    recommended_actions?: string[];
    provider?: string;
  } & Record<string, unknown>;
  created_at: string;
};

export type Site = {
  id: string;
  name: string;
  created_at: string;
};

export type User = {
  id: string;
  email: string;
  role: string;
  created_at: string;
  last_login_at?: string | null;
};

export type ScanJob = {
  id: string;
  site_id: string;
  sensor_id: string;
  schedule_id?: string | null;
  target_cidr: string;
  include_wifi: boolean;
  status: "queued" | "claimed" | "running" | "completed" | "failed" | "canceled" | string;
  created_at: string;
  claimed_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  updated_at: string;
  preview: Record<string, unknown>;
  result_summary: Record<string, unknown>;
  error_message?: string | null;
};

export type ScanSchedule = {
  id: string;
  site_id: string;
  sensor_id: string;
  name: string;
  target_cidr: string;
  frequency: "daily" | "weekly" | string;
  time_of_day: string;
  timezone: string;
  day_of_week?: number | null;
  include_wifi: boolean;
  enabled: boolean;
  next_run_at?: string | null;
  last_run_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type Sensor = {
  id: string;
  site_id: string;
  site_name: string;
  name: string;
  hostname?: string | null;
  status: string;
  connection_state: "online" | "offline" | string;
  version?: string | null;
  os_name?: string | null;
  last_error?: string | null;
  disabled_at?: string | null;
  created_at: string;
  last_seen_at?: string | null;
  current_job?: ScanJob | null;
};

export type NotificationEndpoint = {
  id: string;
  site_id?: string | null;
  name: string;
  type: "webhook" | "email" | "telegram" | string;
  target: string;
  enabled: boolean;
  events: string[];
  last_sent_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
};

export type OnboardingStatus = {
  api_connected: boolean;
  sites_created: boolean;
  sensor_registered: boolean;
  worker_online: boolean;
  first_scan_completed: boolean;
  first_report_generated: boolean;
  schedule_configured: boolean;
  notifications_configured: boolean;
};

export type DashboardData = {
  sites: Site[];
  assets: Asset[];
  wifiNetworks: WifiNetwork[];
  baselines: BaselineRule[];
  findings: Finding[];
  reports: Report[];
  scanJobs: ScanJob[];
  sensors: Sensor[];
  schedules: ScanSchedule[];
  notifications: NotificationEndpoint[];
  onboarding: OnboardingStatus | null;
};
