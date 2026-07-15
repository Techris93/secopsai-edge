# Controlled Pilot Acceptance

Use this checklist after installing a released sensor and before giving an
external operator access. The acceptance command is deliberately
non-destructive: it performs HTTP health/readiness requests and local
capability checks, but never runs Nmap, captures packets, executes packages, or
unpacks artifacts.

## Automated Evidence

From the installed Edge directory:

```bash
./scripts/edge pilot check --cloud --output pilot-acceptance.json
```

For an interactive operator run, add `--format text`. The terminal output is
human-readable and still contains only safe status, error-code, version, and
latency details; `--output` always remains the complete JSON evidence record:

```bash
./scripts/edge pilot check --cloud --format text --output pilot-acceptance.json
```

The JSON record uses `secopsai.edge.pilot-acceptance.v1`. Required checks cover
Nmap, Python, hosted `/healthz`, hosted `/readyz`, the dashboard, and the local
worker service. Wi-Fi capability is recorded as an advisory unless
`--require-wifi` is supplied. The output contains release/schema identity and
error types, never response bodies, tokens, or notification payloads. Hosted
failures include a non-secret `error_code` such as `dns_resolution_failed`,
`network_timeout`, `http_error`, or `invalid_json` so an operator can choose
the right recovery path. The dashboard check also probes its runtime
`/config.js` and verifies non-empty hosted authentication configuration without
recording the configuration body. A reachable page with missing or invalid
runtime configuration therefore fails with an explicit `config_missing` list
instead of looking like a healthy operator console.

For a real operator acceptance run, also verify the authenticated product
surface. Keep the access token in the process environment rather than in the
command line or an evidence file:

```bash
read -r -s SECOPSAI_PILOT_ACCESS_TOKEN
export SECOPSAI_PILOT_ACCESS_TOKEN
./scripts/edge pilot check --cloud --require-auth --output pilot-authenticated.json
unset SECOPSAI_PILOT_ACCESS_TOKEN
```

When the token is present, the check verifies authenticated identity, system
status, onboarding, sites, sensors, schedules, findings, and reports. It
records only endpoint status, latency, and JSON validity. It never records the
token or response bodies. Use `--require-auth` for the external pilot gate;
without it, the authenticated check is reported as an advisory.

Useful variants:

```bash
# Validate a local development installation without hosted checks.
./scripts/edge pilot check --skip-cloud --output pilot-local.json

# Validate a host before installing the worker service.
./scripts/edge pilot check --cloud --skip-worker --output pilot-preflight.json

# Require an authorized Linux Wi-Fi inventory capability for a sensor build.
./scripts/edge pilot check --cloud --require-wifi --output pilot-wireless.json

# Verify the hosted API and authenticated operator surfaces.
SECOPSAI_PILOT_ACCESS_TOKEN="$PILOT_TOKEN" \
  ./scripts/edge pilot check --cloud --require-auth --output pilot-authenticated.json
```

## Operator Acceptance Matrix

Record the operator, timestamp, release, site, and evidence path for each row.

| Area | Acceptance evidence |
| --- | --- |
| Fresh install | Release checksum verified; installer completes on the target host; worker survives a restart. |
| Authorization | Target CIDR is owned or explicitly authorized; preview output is reviewed before the first scan. |
| First inventory | Assets, services, and Wi-Fi source/interface provenance appear in the selected site. |
| Change detection | A controlled test device or approved fixture creates a new-device or port-change finding. |
| Schedule | A daily or weekly schedule queues one job at the intended timezone; last and next run are visible. |
| Notifications | One approved email, Telegram, or signed webhook destination receives a test event; delivery state is visible. |
| Recovery | Two owners complete invitation, MFA, recovery-code, owner-reset, and session-revocation exercises. |
| Hosted durability | Paid always-on API/database plan is active; a provider recovery point is restored into a separate database and `/readyz` is verified. |
| Support | A redacted support bundle is reviewed and can be shared without credentials or raw telemetry. |
| Exit | Site export, final report, schedule/sensor disablement, uninstall, and owner-confirmed deletion are recorded. |

## Seven-Day Soak

During the soak, retain only non-secret evidence:

- one `pilot-acceptance.json` per validation event;
- scheduled scan/job history and notification delivery status;
- daily hosted readiness checks from an independent network;
- sensor version, heartbeat, and last-error observations;
- the final report and any support bundle shared with the operator.

The soak is not complete when the dashboard merely loads. It is complete when
the operator can understand a change, triage it, generate a report, recover
from a worker or account problem, and exit without founder-only intervention.

## Boundaries

- The current macOS path is legacy `airport` metadata inventory only.
- Linux `iw` support is managed-mode metadata collection. TL-WN722N V4
  behavior remains chipset/driver dependent and must be tested on the actual
  authorized Linux/Raspberry Pi host.
- Do not use this checklist as permission to scan a third-party network or to
  execute an untrusted package outside a disposable, controlled environment.
