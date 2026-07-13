# SecOpsAI Core Integration

SecOpsAI Edge exports a normalized graph and finding bundle for the main SecOpsAI Core local SOC store.

## Export

One-step local Core sync:

```bash
./scripts/edge core sync --cloud --core-root "$HOME/secopsai" --output edge-bundle.json
```

This exports the normalized Edge bundle from the configured API, saves it for audit/review, and imports it into the main SecOpsAI Core SQLite SOC/graph store.

## Automatic Sync

Install a supervised five-minute sync on the machine that runs Core:

```bash
./scripts/edge core sync-service install --cloud --core-root "$HOME/secopsai" --interval 300
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

macOS uses a launchd interval job. Linux uses a systemd user timer and one-shot service. The scanner worker and Core sync have separate lifecycle, logs, and failure boundaries. The installer stages a small runner under Application Support (macOS) or the user data directory (Linux), so launchd does not need access to a repository under a privacy-protected Documents folder. Configuration and credentials are separate owner-only JSON files; the token is passed to Core through the child environment, never process arguments or the plist/unit. An advisory file lock skips overlapping timer/manual runs.

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
Authorization: Bearer <admin-token>
```

## Unified Operator Workspace

The canonical SecOpsAI dashboard reads network assets, graph changes, and
Edge-origin findings from Core. Its local/helper service can optionally enrich
that view with live sites, sensors, schedules, and scan jobs from the Edge API.

Keep `SECOPSAI_EDGE_ADMIN_TOKEN` on the helper host only. The browser receives
normalized workspace data and never receives the administrator token. Scan and
sensor administration remains in the Edge dashboard; Core remains canonical
for finding triage and graph context.

## Contract

The bundle uses:

```json
{
  "schema_version": "secopsai.edge.bundle.v1",
  "exported_at": "2026-06-28T10:00:00Z",
  "source_instance": {
    "product": "secopsai_edge",
    "api": "secopsai-edge-api",
    "version": "0.1.0"
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
