# SecOpsAI Core Integration

SecOpsAI Edge exports a normalized graph and finding bundle for the main SecOpsAI Core local SOC store.

## Export

One-step local Core sync:

```bash
./scripts/edge core sync --cloud --core-root /Users/chrixchange/secopsai --output edge-bundle.json
```

This exports the normalized Edge bundle from the configured API, saves it for audit/review, and imports it into the main SecOpsAI Core SQLite SOC/graph store.

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
