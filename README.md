# SecOpsAI Edge Sensor

Standalone MacBook-first MVP for an AI-assisted asset discovery and wireless intelligence sensor.

## What Is Included

- Native Python collection agent using safe, allowlisted Nmap scans.
- FastAPI backend with PostgreSQL, migrations, auth, audit logs, findings, reports, and Splunk HEC export hooks.
- Next.js/Tailwind dashboard for assets, Wi-Fi networks, findings, reports, and sensor settings.
- Docker Compose for local PostgreSQL.
- Tests for scan safety, Nmap parsing, detection rules, and AI payload redaction.

## Quick Start

The easiest path is to use the project helper:

```bash
./scripts/edge setup
./scripts/edge dev
```

Then open:

[http://127.0.0.1:3000](http://127.0.0.1:3000)

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

## Useful Commands

```bash
./scripts/edge status
./scripts/edge test
./scripts/edge stop-db
```

Cloud commands:

```bash
./scripts/edge cloud configure https://<your-render-api>.onrender.com
./scripts/edge cloud register
./scripts/edge scan 192.168.1.0/24 --cloud
./scripts/edge report --cloud
```

See [docs/architecture.md](docs/architecture.md) and [docs/runbook.md](docs/runbook.md) for implementation details.

## Hosting

Use Render for the API/PostgreSQL and Cloudflare Pages for the static dashboard. The scanner stays
local on your MacBook or Raspberry Pi.

See [docs/render-cloudflare-deploy.md](docs/render-cloudflare-deploy.md).
