import type { DashboardData } from "./types";

const now = new Date().toISOString();

export const sampleData: DashboardData = {
  sites: [
    {
      id: "site-demo",
      organization_id: "organization-demo",
      name: "Demo Site",
      created_at: now
    }
  ],
  assets: [
    {
      id: "asset-1",
      site_id: "site-demo",
      ip_address: "192.168.1.12",
      mac_address: "aa:bb:cc:dd:ee:01",
      vendor: "Apple",
      hostname: "finance-macbook",
      os_guess: "macOS",
      device_type: "workstation",
      status: "active",
      first_seen_at: now,
      last_seen_at: now,
      services: []
    },
    {
      id: "asset-2",
      site_id: "site-demo",
      ip_address: "192.168.1.34",
      mac_address: null,
      vendor: "Unknown",
      hostname: null,
      os_guess: null,
      device_type: null,
      status: "active",
      first_seen_at: now,
      last_seen_at: now,
      services: [
        {
          id: "svc-1",
          port: 22,
          protocol: "tcp",
          name: "ssh",
          product: null,
          version: null,
          state: "open",
          first_seen_at: now,
          last_seen_at: now
        }
      ]
    }
  ],
  wifiNetworks: [
    {
      id: "wifi-1",
      site_id: "site-demo",
      ssid: "OfficeWiFi",
      bssid: "00:11:22:33:44:55",
      channel: 6,
      signal: -48,
      encryption: "WPA2",
      source: "macos:airport",
      status: "active",
      first_seen_at: now,
      last_seen_at: now
    },
    {
      id: "wifi-2",
      site_id: "site-demo",
      ssid: "OfficeWiFi_Open",
      bssid: "66:77:88:99:aa:bb",
      channel: 11,
      signal: -62,
      encryption: "Open",
      source: "linux:iw:wlan1",
      status: "active",
      first_seen_at: now,
      last_seen_at: now
    }
  ],
  baselines: [],
  findings: [
    {
      id: "finding-1",
      site_id: "site-demo",
      asset_id: "asset-2",
      type: "new_device",
      severity: "medium",
      status: "open",
      title: "New device detected",
      summary: "A previously unseen device appeared at 192.168.1.34.",
      evidence: { ip: "192.168.1.34", vendor: "Unknown" },
      mitre_attack: [{ id: "T1046", name: "Network Service Discovery" }],
      created_at: now,
      updated_at: now
    },
    {
      id: "finding-2",
      site_id: "site-demo",
      wifi_network_id: "wifi-2",
      type: "weak_wifi",
      severity: "high",
      status: "open",
      title: "Weak or open Wi-Fi network detected",
      summary: "OfficeWiFi_Open is advertising weak or missing encryption.",
      evidence: { ssid: "OfficeWiFi_Open", encryption: "Open" },
      mitre_attack: [{ id: "T1557", name: "Adversary-in-the-Middle" }],
      created_at: now,
      updated_at: now
    }
  ],
  reports: [
    {
      id: "report-1",
      site_id: "site-demo",
      title: "SecOpsAI Edge Weekly Security Summary",
      summary: "SecOpsAI Edge found 2 active security findings. 1 requires priority review.",
      risk_level: "high",
      content: {
        recommended_actions: [
          "Validate ownership for new or unknown devices.",
          "Confirm Wi-Fi SSIDs and BSSIDs match authorized infrastructure."
        ],
        provider: "demo"
      },
      created_at: now
    }
  ],
  scanJobs: [],
  sensorEnrollments: [],
  schedules: [],
  notifications: [],
  onboarding: {
    api_connected: false,
    sites_created: true,
    sensor_registered: true,
    worker_online: false,
    first_scan_completed: false,
    first_report_generated: true,
    schedule_configured: false,
    notifications_configured: false
  },
  sensors: [
    {
      id: "sensor-demo",
      site_id: "site-demo",
      site_name: "Demo Site",
      name: "MacBook Sensor",
      hostname: "macbook",
      status: "offline",
      connection_state: "offline",
      created_at: now,
      last_seen_at: null,
      current_job: null
    }
  ]
};
