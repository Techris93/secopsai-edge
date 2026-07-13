# SecOpsAI Core Integration

SecOpsAI Edge exports a normalized graph and finding bundle for the main
SecOpsAI Core store. Core can remain local-first or receive the bundle through
its protected hosted ingestion API.

## Export

One-step local Core sync:

```bash
SECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core export token: "))')"; export SECOPSAI_EDGE_CORE_TOKEN
./scripts/edge core sync --cloud --core-root "$HOME/secopsai" --output edge-bundle.json
unset SECOPSAI_EDGE_CORE_TOKEN
```

This exports the normalized Edge bundle from the configured API, saves it for audit/review, and imports it into the main SecOpsAI Core SQLite SOC/graph store.

## Push To A Hosted Core API

The hosted path uses two unrelated credentials: a workspace-scoped
`core:export` token from Edge and the organization-bound ingest token from the
Core deployment. Neither credential is placed in a process argument.

```bash
export SECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Edge Core export token: "))')"
export SECOPSAI_CORE_INGEST_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core ingest token: "))')"
./scripts/edge core push --cloud \
  --core-api-url https://secopsai-core-api.onrender.com \
  --output edge-bundle.json
unset SECOPSAI_EDGE_CORE_TOKEN SECOPSAI_CORE_INGEST_TOKEN
```

The transfer rejects non-loopback plain HTTP, redirects, responses larger than
the contract limit, and a Core response that does not confirm import. The
saved bundle is owner-only and remains useful for audit/recovery.

## Automatic Sync

Install a supervised five-minute sync on the machine that runs Core:

```bash
SECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core export token: "))')"; export SECOPSAI_EDGE_CORE_TOKEN
./scripts/edge core sync-service install --cloud --core-root "$HOME/secopsai" --interval 300
unset SECOPSAI_EDGE_CORE_TOKEN
./scripts/edge core sync-service start
```

Operate and recover it with:

```bash
./scripts/edge core sync-service status
./scripts/edge core sync-service logs
./scripts/edge core sync-service run-now
./scripts/edge core sync-service stop
./scripts/edge core sync-service uninstall
```

Create the expiring, workspace-scoped `core:export` token in Dashboard >
Settings > SecOpsAI Core Integration. macOS uses a launchd interval job. Linux
uses a systemd user timer and one-shot service. The scanner worker and Core
sync have separate lifecycle, logs, and failure boundaries. The installer
stages a small runner under Application Support (macOS) or the user data
directory (Linux), so launchd does not need access to a repository under a
privacy-protected Documents folder. Configuration and credentials are separate
owner-only JSON files; the token is passed to Core through the child
environment, never process arguments or the plist/unit. An advisory file lock
skips overlapping timer/manual runs.

For hosted Core, install the same supervised service without a local Core
checkout:

```bash
export SECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Edge Core export token: "))')"
export SECOPSAI_CORE_INGEST_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core ingest token: "))')"
./scripts/edge core sync-service install --cloud \
  --core-api-url https://secopsai-core-api.onrender.com \
  --interval 300
unset SECOPSAI_EDGE_CORE_TOKEN SECOPSAI_CORE_INGEST_TOKEN
./scripts/edge core sync-service start
```

Local API:

```bash
./scripts/edge core export --output edge-bundle.json
```

Hosted Render API:

```bash
./scripts/edge core export --cloud --output edge-bundle.json
```

The API endpoint is:

```text
GET /api/v1/core/export
Authorization: Bearer <workspace-core-export-token>
```

## Unified Operator Workspace

The canonical SecOpsAI dashboard reads network assets, graph changes, and
Edge-origin findings from Core. Its local/helper service can optionally enrich
that view with live sites, sensors, schedules, and scan jobs from the Edge API.

After a sync, Core operators and OpenClaw can inspect freshness without
running another import:

```bash
secopsai edge status
```

The equivalent OpenClaw read-only action is `secopsai_edge_sync_status`. Both
surfaces report the source identity, contract version, bundle timestamp, local
sync timestamp, and cursor; neither exposes raw scan telemetry.

## Approval-Gated Scan Requests

The OpenClaw plugin can request a hosted scan without executing Nmap itself:

```text
secopsai_edge_request_scan targetCidr=192.168.1.0/24 includeWifi=false
secopsai_session_show sessionId=SES-...
secopsai_session_resolve_approval sessionId=SES-... approvalId=APR-... decision=approved apply=true
```

The request is recorded in Core as a session approval. On approval, Core
invokes the configured Edge installation's `scripts/edge queue` helper with
structured arguments. Edge performs the final RFC1918 `/24`-or-narrower
validation and queues the job for the local worker. Core keeps only normalized
approval and queue metadata; credentials, helper output, and raw scan logs
remain local.

Report and worker lifecycle requests use the same pattern:

```text
secopsai_edge_request_report
secopsai_edge_request_worker_action action=start
secopsai_session_resolve_approval sessionId=SES-... approvalId=APR-... decision=approved apply=true
```

The allowlisted Edge helper actions are `report --cloud`, `worker start`, and
`worker stop`. They are never executed directly by OpenClaw.

Use two separate helper-host credentials:

- `SECOPSAI_EDGE_ACCESS_TOKEN` has `core:export` and can read only the
  normalized Core bundle for its workspace.
- `SECOPSAI_EDGE_OPERATIONS_TOKEN` has `operations:read` and can read only
  sites, sensors, schedules, and scan-job status for its workspace.

Create each credential from Dashboard > Settings > SecOpsAI Core Integration.
The browser receives normalized workspace data and never receives either token
after its one-time creation response. Neither scope can mutate scans, sensors,
users, or settings. Scan and sensor administration remains in the Edge
dashboard; Core remains canonical for finding triage and graph context.

Each scoped credential can inspect only its own non-secret lifecycle metadata
at `GET /api/v1/integration-tokens/self`. Edge and the canonical dashboard warn
when 14 days remain. To rotate without downtime:

1. Choose **Rotate** beside the credential in Edge Settings.
2. Copy the replacement secret when it is shown once.
3. Update the Core sync service or canonical dashboard helper.
4. Verify one successful sync or Edge workspace refresh.
5. Revoke the previous credential, using its short ID and creation timestamp to
   distinguish it from the replacement.

Rotation deliberately keeps the previous credential active until step 5.

## Contract

The bundle uses:

```json
{
  "schema_version": "secopsai.edge.bundle.v1",
  "exported_at": "2026-06-28T10:00:00Z",
  "source_instance": {
    "product": "secopsai_edge",
    "api": "secopsai-edge-api",
    "version": "0.3.7",
    "organization_id": "<edge-workspace-id>"
  },
  "cursor": {
    "mode": "full",
    "last_observed_at": "2026-06-28T10:00:00Z"
  },
  "graph": {
    "nodes": [],
    "edges": []
  },
  "findings": []
}
```

Node types:

- `site`
- `sensor`
- `scan`
- `asset`
- `service`
- `wifi_network`

Edge types:

- `site_has_sensor`
- `sensor_ran_scan`
- `scan_observed_asset`
- `asset_exposes_service`
- `sensor_observed_wifi`

## Privacy Boundary

The export contains normalized inventory, graph relationships, and findings. It does not include raw Nmap XML, packet captures, packet payloads, or raw scan logs.
