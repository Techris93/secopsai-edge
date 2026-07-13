# Architecture

## Runtime Shape

```mermaid
flowchart LR
  MacBook["MacBook Sensor Agent"] -->|normalized scan payload| API["FastAPI Backend"]
  API --> DB["PostgreSQL"]
  API --> AI["AI Report Adapter"]
  API --> Splunk["Splunk HEC Optional"]
  Web["Next.js Dashboard"] --> API
  API -->|"normalized bundle"| Sync["Supervised Core Sync"]
  Sync --> Core["SecOpsAI Core SOC + Asset Graph"]
```

## Local Sensor

The agent runs natively on macOS and uses Nmap for safe active discovery. It validates CIDR targets before executing scans, rejects public ranges by default, and limits scan size. The agent can also collect macOS Wi-Fi observations when the local wireless tooling exposes scan data.

The API receives normalized observations only:

- Asset identifiers: IP, optional MAC, vendor, hostname, OS guess, device type.
- Service observations: protocol, port, state, service name, product, version.
- Wi-Fi observations: SSID, BSSID, channel, signal, encryption.

Raw scanner output is intentionally not submitted to the backend by the default client.

## Backend

FastAPI owns ingestion, inventory merge logic, finding generation, reporting, and exports. PostgreSQL is the durable store. Alembic migrations define the initial schema.

The dashboard exposes the append-only audit stream for pilot operations. The local helper can create an owner-readable diagnostics bundle containing release, dependency, API, worker, and redacted log state for support recovery.

Core tables:

- `sites`
- `sensors`
- `scan_runs`
- `assets`
- `asset_observations`
- `services`
- `wifi_networks`
- `baseline_rules`
- `findings`
- `reports`
- `users`
- `audit_logs`
- `scan_schedules`
- `notification_endpoints`
- `notification_deliveries`

## Detection Rules

Version one includes deterministic findings for:

- New devices.
- Missing devices in the scanned CIDR.
- Unknown vendors.
- Risky open ports.
- Open port changes.
- Weak or open Wi-Fi networks.
- Duplicate SSID with a newly observed BSSID.

Operators can approve known assets, accepted services, and trusted BSSIDs with site-scoped baseline rules. Asset approval acknowledges new-device and unknown-vendor noise. Service approval is exact to an asset, port, and protocol. BSSID approval suppresses duplicate-SSID noise but intentionally leaves weak/open-encryption findings active. Rules can expire or be disabled, and disabling a rule reopens findings acknowledged by that rule.

Suspicious scan-like behavior is left as a future rule because the MVP does not yet collect netflow or firewall/session telemetry.

## AI Boundary

The AI provider receives minimized finding payloads, not raw Nmap output, packet data, or full scan logs. The default provider is `mock`, which gives deterministic report output for local development. OpenAI Structured Outputs can be enabled with `AI_PROVIDER=openai`, `AI_API_KEY`, and `AI_MODEL`. A generic HTTP provider remains available with `AI_PROVIDER=http` and `AI_ENDPOINT`.

## SecOpsAI Core Integration

Edge exports the versioned `secopsai.edge.bundle.v1` contract. A supervised launchd/systemd timer can export the normalized graph and findings from the hosted or local Edge API and import them into Core's SQLite SOC/graph store. The service is one-way, idempotent, separately logged, and does not share databases or move raw scanner output. Hosted Core ingestion, tenant isolation, billing, fleet management, and remote update orchestration remain later SaaS milestones.
