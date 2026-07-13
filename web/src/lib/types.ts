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
  period_start?: string | null;
  period_end?: string | null;
  content: {
    findings?: Finding[];
    recommended_actions?: string[];
    provider?: string;
    model?: string;
    technical_notes?: string[];
    period?: { start: string; end: string };
    metrics?: {
      assets_total: number;
      assets_active?: number;
      new_devices: number;
      risky_services: number;
      wifi_security_findings: number;
      open_findings: number;
      acknowledged_findings: number;
      resolved_findings: number;
      scans_completed: number;
      severity: Record<string, number>;
    };
  } & Record<string, unknown>;
  created_at: string;
};

export type Site = {
  id: string;
  organization_id: string;
  name: string;
  created_at: string;
};

export type DataLifecyclePolicy = {
  organization_id: string;
  observation_days: number;
  scan_history_days: number;
  notification_delivery_days: number;
  account_access_days: number;
  credential_history_days: number;
  report_days: number;
  audit_log_days: number;
  last_run_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type DataLifecycleRun = {
  organizations: number;
  skipped: number;
  deleted: Record<string, number>;
  run_at: string;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  active: boolean;
  role: "owner" | "admin" | "viewer" | string;
  created_at: string;
};

export type AuthIdentity = {
  subject: string;
  role: string;
  organization_id: string;
  organizations: Organization[];
  user?: User | null;
};

export type SystemStatus = {
  status: "ready" | "degraded" | string;
  environment: string;
  version: string;
  commit: string;
  schema_revision?: string | null;
  expected_schema_revision: string;
  ai_provider: string;
  organization_id: string;
  server_time: string;
};

export type User = {
  id: string;
  email: string;
  role: string;
  active: boolean;
  created_at: string;
  last_login_at?: string | null;
  password_changed_at?: string | null;
  mfa_enabled: boolean;
};

export type UserInvitation = {
  id: string;
  user_id: string;
  organization_id: string;
  email: string;
  role: string;
  state: "pending" | "accepted" | "revoked" | "expired" | "closed" | string;
  delivery_status: string;
  expires_at: string;
  created_at: string;
};

export type AccountAccessDelivery = {
  id: string;
  user_id: string;
  email: string;
  purpose: string;
  status: "queued" | "retrying" | "delivered" | "failed" | string;
  attempts: number;
  max_attempts: number;
  expires_at: string;
  next_attempt_at: string;
  last_attempt_at?: string | null;
  delivered_at?: string | null;
  detail?: string | null;
  created_at: string;
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
  worker_state?: string | null;
  current_job_id?: string | null;
  last_error?: string | null;
  disabled_at?: string | null;
  created_at: string;
  last_seen_at?: string | null;
  current_job?: ScanJob | null;
};

export type SensorEnrollment = {
  id: string;
  organization_id: string;
  site_id: string;
  site_name: string;
  label: string;
  state: "active" | "used" | "expired" | "revoked" | string;
  expires_at: string;
  used_at?: string | null;
  revoked_at?: string | null;
  created_at: string;
};

export type SensorEnrollmentSecret = SensorEnrollment & {
  enrollment_token: string;
};

export type IntegrationToken = {
  id: string;
  organization_id: string;
  name: string;
  scopes: string[];
  state: "active" | "expired" | "revoked" | string;
  expires_at: string;
  expires_in_days: number;
  rotation_recommended: boolean;
  last_used_at?: string | null;
  revoked_at?: string | null;
  created_at: string;
};

export type IntegrationTokenSecret = IntegrationToken & {
  access_token: string;
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

export type NotificationDelivery = {
  id: string;
  endpoint_id: string;
  site_id?: string | null;
  event_type: string;
  status: "queued" | "retrying" | "delivered" | "failed" | string;
  attempts: number;
  max_attempts: number;
  next_attempt_at: string;
  last_attempt_at?: string | null;
  delivered_at?: string | null;
  response_detail?: string | null;
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
  sensorEnrollments: SensorEnrollment[];
  schedules: ScanSchedule[];
  notifications: NotificationEndpoint[];
  onboarding: OnboardingStatus | null;
};
