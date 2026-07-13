# SecOpsAI Edge Sensor

Current pilot release: [`v0.3.6`](https://github.com/Techris93/secopsai-edge/releases/tag/v0.3.6).

Standalone MacBook-first MVP for an AI-assisted asset discovery and wireless intelligence sensor.

## What Is Included

- Native Python collection agent using safe, allowlisted Nmap scans.
- FastAPI backend with PostgreSQL, workspace isolation, role-based auth, audit logs, approved baselines, findings, reports, and Splunk HEC export hooks.
- Next.js/Tailwind dashboard for onboarding, sites, assets, Wi-Fi networks, findings, schedules, reports, notifications, and sensor settings.
- Explicit macOS/Linux Wi-Fi capability diagnostics and managed-mode inventory
  provenance; see `docs/wireless-support.md` before enabling adapter scans.
- Guided onboarding, launchd/systemd worker service installation, scheduled scans, sensor token rotation, and client-ready PDF/HTML report export.
- One-time operator invitations, self-service account recovery, optional TOTP MFA,
  one-use recovery codes, session revocation, and account-delivery diagnostics.
- Scoped Core/dashboard credentials with advance expiry warnings and overlap-safe rotation.
- Docker Compose for local PostgreSQL.
- Tests for scan safety, Nmap parsing, detection rules, and AI payload redaction.
- Workspace retention controls plus normalized customer export and owner-confirmed site deletion.

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

For a released sensor, use the one-time command copied from Sites. It downloads
the standalone bootstrap, verifies the release checksum, and installs the
background worker without cloning the repository:

```bash
gh auth login
gh release download --repo Techris93/secopsai-edge --pattern bootstrap-secopsai-edge.sh --clobber
bash bootstrap-secopsai-edge.sh --cloud --api-url https://<your-api>.onrender.com --enrollment-token <one-time-token>
```

The repository is private during the pilot, so installers need collaborator
access and an authenticated GitHub CLI. A future public release can use the
same bootstrap through the unauthenticated HTTPS download URL.

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

Authenticated users can switch among their assigned workspaces from the global selector. Sites,
sensors, assets, findings, schedules, reports, notifications, audit records, and Core exports are
restricted to the active workspace. Owners can create another customer workspace; administrators
manage sites and invite members, while viewers have read-only access. Invited operators choose
their own password from a one-time link. They can then enable authenticator-app MFA and store the
one-use recovery codes from Settings; no administrator needs to share a temporary password.

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

Queue a hosted job for the local worker:

```bash
./scripts/edge queue 192.168.1.0/24 --cloud
```

Queueing does not run Nmap in Core or on Render. The helper and Edge API both
restrict the target to an authorized RFC1918 `/24` or narrower network.

Generate a report:

```bash
./scripts/edge report
```

Open Reports in the dashboard, select the generated report, and choose
`Download PDF` for a shareable A4 report. The exported artifact freezes its
seven-day reporting period and operational metrics at generation time and
contains normalized findings only. HTML download and browser print remain
available as fallbacks.

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
./scripts/edge release-check
./scripts/edge database backup
./scripts/edge cloud drift-check
./scripts/edge cloud backup
./scripts/edge cloud uptime-check --output hosted-health.jsonl
./scripts/edge pilot check --cloud --output pilot-acceptance.json
./scripts/edge worker status
./scripts/edge worker logs
./scripts/edge schedules run-due --cloud
./scripts/edge stop-db
```

`./scripts/edge test` runs backend and agent tests, frontend component tests,
the production dashboard build, desktop/mobile Chromium workflow tests, and the
frontend dependency audit. A normal `./scripts/edge setup` installs the browser
runtime; sensor-only appliance installs omit all dashboard test dependencies.

Cloud commands:

```bash
./scripts/edge cloud configure https://<your-render-api>.onrender.com
./scripts/edge cloud register
./scripts/edge cloud rotate-sensor-token
./scripts/edge cloud drift-check
./scripts/edge cloud backup
./scripts/edge worker install-service --cloud
./scripts/edge worker start
./scripts/edge worker restart
./scripts/edge worker --cloud
./scripts/edge scan 192.168.1.0/24 --cloud
./scripts/edge report --cloud
SECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core export token: "))')"; export SECOPSAI_EDGE_CORE_TOKEN
./scripts/edge core sync --cloud --core-root "$HOME/secopsai" --output edge-bundle.json
unset SECOPSAI_EDGE_CORE_TOKEN
```

When Core runs behind its protected HTTP API, push the same minimized bundle
without requiring a Core checkout on the sensor host:

```bash
export SECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Edge Core export token: "))')"
export SECOPSAI_CORE_INGEST_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core ingest token: "))')"
./scripts/edge core push --cloud --core-api-url https://<core-api>.onrender.com
unset SECOPSAI_EDGE_CORE_TOKEN SECOPSAI_CORE_INGEST_TOKEN
```

The hosted dashboard can also queue remote scan jobs. Keep the worker running locally so queued jobs
execute on your MacBook/Raspberry Pi, where the LAN is actually reachable. The dashboard shows
sensor online/offline status from worker heartbeats and provides cancel/retry controls for remote jobs.

If a sensor credential is lost or suspected to be exposed, rotate it from the
dashboard Sites page or from the local helper. The CLI asks for the hosted
administrator credential without saving it, replaces `.cloud-sensor.env`
atomically with owner-only permissions, and never prints the replacement token:

```bash
./scripts/edge cloud rotate-sensor-token
./scripts/edge worker restart
```

Use `./scripts/edge cloud reauth <sensor-id>` when the saved sensor ID is not
available. The old token stops working immediately after the API rotation.

See [docs/architecture.md](docs/architecture.md) and [docs/runbook.md](docs/runbook.md) for implementation details.

Before inviting an external operator, run the non-destructive acceptance check
and attach its JSON output to the pilot record:

```bash
./scripts/edge pilot check --cloud --output pilot-acceptance.json
```

This verifies the local runtime and hosted liveness/readiness without scanning
the network. Paid hosting/PITR, a real notification exercise, second-owner
MFA/recovery, fresh-host soak, and any in-scope Wi-Fi hardware validation still
require operator evidence; a green local test suite does not replace those
checks. See [docs/pilot-acceptance.md](docs/pilot-acceptance.md).

Pilot docs:

- [docs/install-sensor.md](docs/install-sensor.md)
- [docs/pilot-guide.md](docs/pilot-guide.md)
- [docs/pilot-acceptance.md](docs/pilot-acceptance.md)
- [docs/demo-script.md](docs/demo-script.md)
- [docs/security-boundaries.md](docs/security-boundaries.md)
- [docs/msp-pilot.md](docs/msp-pilot.md)
- [docs/data-lifecycle.md](docs/data-lifecycle.md)

## Hosting

Use Render for the API/PostgreSQL and Cloudflare Pages for the static dashboard. The scanner stays
local on your MacBook or Raspberry Pi.

See [docs/render-cloudflare-deploy.md](docs/render-cloudflare-deploy.md).
