# Roadmap

## Phase 1: MacBook Pilot MVP — Code Complete 2026-06-27

Phase 1 is code-complete when `./scripts/edge test` passes and the cloud smoke test succeeds against the hosted Render API and Cloudflare Pages dashboard.

Completed scope:

- Asset discovery.
- Device inventory.
- Risky service detection.
- AI reports.
- Dashboard.
- Splunk HEC export.
- Hosted remote scan queue with local MacBook worker execution.
- Sensor online/offline visibility, worker heartbeat, job cancel/retry, and stale job recovery.
- Site-scoped asset, service, and trusted-BSSID baselines.
- Dashboard audit-log review and redacted support bundles.

Pilot-readiness checks:

- Run `./scripts/edge status --cloud`.
- Run `./scripts/edge worker --cloud` during dashboard-driven scans.
- Queue a remote scan from the dashboard and confirm it completes.
- Generate a report from live cloud data.
- Confirm production admin/sensor token handling before demos.
- Confirm Splunk HEC with a real endpoint if Splunk export will be demonstrated.

## Phase 2: Wireless Intelligence

- Validate TL-WN722N support on macOS and Raspberry Pi.
- Improve Wi-Fi scanner adapters.
- Expand authorized SSID/BSSID baselines into a full rogue-AP review workflow.
- Add rogue AP review workflow.

## Phase 3: Behavior Analytics

- Add passive network telemetry sources.
- Detect internal scanning behavior from connection observations.
- Add beaconing and brute-force detection when logs are available.
- Map more findings to MITRE ATT&CK.

## Phase 4: Commercial SaaS

- Multi-site fleet management.
- Tenant isolation.
- Remote sensor updates.
- Billing and MSP deployment model.
- Customer-ready onboarding and support tooling.
