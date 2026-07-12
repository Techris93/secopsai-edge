# SecOpsAI Edge Sensor

Standalone MacBook-first MVP for an AI-assisted asset discovery and wireless intelligence sensor.

## What Is Included

- Native Python collection agent using safe, allowlisted Nmap scans.
- FastAPI backend with PostgreSQL, migrations, auth, audit logs, approved baselines, findings, reports, and Splunk HEC export hooks.
- Next.js/Tailwind dashboard for onboarding, sites, assets, Wi-Fi networks, findings, schedules, reports, notifications, and sensor settings.
- Guided onboarding, launchd/systemd worker service installation, scheduled scans, sensor token rotation, and report export.
- Docker Compose for local PostgreSQL.
- Tests for scan safety, Nmap parsing, detection rules, and AI payload redaction.

## Product Role

SecOpsAI Edge is the network discovery and sensor module for the wider SecOpsAI product:

- Main product: [secopsai.dev](https://secopsai.dev)
- Research and advisories: [blog.secopsai.dev](https://blog.secopsai.dev)
- Operator documentation: [docs.secopsai.dev](https://docs.secopsai.dev)

Edge owns local LAN discovery, Wi-Fi inventory, scan jobs, worker heartbeat, and safe telemetry minimization. Main SecOpsAI should own long-term graph context, canonical findings, triage, reports, research intelligence, and AI memory.

## Quick Start

The easiest hosted pilot path is:

```bash
./scripts/edge onboard --cloud --install-service --start-service
```

Or use the installer wrapper:

```bash
./scripts/install-secopsai-edge.sh --cloud --api-url https://<your-api>.onrender.com --admin-token <admin-token>
```

The local development path is:

```bash
./scripts/edge setup
./scripts/edge dev
```

Then open:

[http://127.0.0.1:3000](http://127.0.0.1:3000)

The dashboard shows one of three data states:

- `Live API data`: connected to the configured API with a browser session.
- `API not connected`: no usable API/session, so pilot telemetry is not being displayed.
- `Demo data only`: sample telemetry is shown only when `NEXT_PUBLIC_SECOPSAI_DEMO_MODE=true` is explicitly configured.

In another terminal, register this MacBook as a sensor:

```bash
./scripts/edge register
```

Preview the exact safe Nmap command before scanning:

```bash
./scripts/edge preview 192.168.1.0/24
```

Submit a scan:

```bash
./scripts/edge scan 192.168.1.0/24
```

Generate a report:

```bash
./scripts/edge report
```

Replace `192.168.1.0/24` with your own authorized local network.

## Safety Defaults

- Public IP ranges are rejected by default.
- Scans are limited to private CIDR ranges with a maximum host count.
- Nmap uses conservative timing, retries, and timeouts.
- Raw Nmap output is retained by the agent only; AI reports receive normalized findings.
- Approved baselines are site-scoped, audited, reversible, and never hide weak Wi-Fi encryption by default.

## Useful Commands

```bash
./scripts/edge status
./scripts/edge support-bundle --cloud
./scripts/edge test
./scripts/edge worker status
./scripts/edge worker logs
./scripts/edge schedules run-due --cloud
./scripts/edge stop-db
```

Cloud commands:

```bash
./scripts/edge cloud configure https://<your-render-api>.onrender.com
./scripts/edge cloud register
./scripts/edge worker install-service --cloud
./scripts/edge worker start
./scripts/edge worker --cloud
./scripts/edge scan 192.168.1.0/24 --cloud
./scripts/edge report --cloud
./scripts/edge core sync --cloud --core-root /Users/chrixchange/secopsai --output edge-bundle.json
```

The hosted dashboard can also queue remote scan jobs. Keep the worker running locally so queued jobs
execute on your MacBook/Raspberry Pi, where the LAN is actually reachable. The dashboard shows
sensor online/offline status from worker heartbeats and provides cancel/retry controls for remote jobs.

See [docs/architecture.md](docs/architecture.md) and [docs/runbook.md](docs/runbook.md) for implementation details.

Pilot docs:

- [docs/install-sensor.md](docs/install-sensor.md)
- [docs/pilot-guide.md](docs/pilot-guide.md)
- [docs/demo-script.md](docs/demo-script.md)
- [docs/security-boundaries.md](docs/security-boundaries.md)
- [docs/msp-pilot.md](docs/msp-pilot.md)

## Hosting

Use Render for the API/PostgreSQL and Cloudflare Pages for the static dashboard. The scanner stays
local on your MacBook or Raspberry Pi.

See [docs/render-cloudflare-deploy.md](docs/render-cloudflare-deploy.md).
