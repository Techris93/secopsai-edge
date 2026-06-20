export type Severity = "critical" | "high" | "medium" | "low";

export type Asset = {
  id: string;
  ip_address: string;
  mac_address?: string | null;
  vendor?: string | null;
  hostname?: string | null;
  os_guess?: string | null;
  device_type?: string | null;
  status: string;
  first_seen_at: string;
  last_seen_at: string;
};

export type WifiNetwork = {
  id: string;
  ssid: string;
  bssid?: string | null;
  channel?: number | null;
  signal?: number | null;
  encryption?: string | null;
  status: string;
  first_seen_at: string;
  last_seen_at: string;
};

export type Finding = {
  id: string;
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

export type Report = {
  id: string;
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

export type DashboardData = {
  assets: Asset[];
  wifiNetworks: WifiNetwork[];
  findings: Finding[];
  reports: Report[];
};
