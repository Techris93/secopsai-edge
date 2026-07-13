# Runbook

## Start Local Services

```bash
./scripts/edge setup
./scripts/edge dev
```

This starts PostgreSQL, runs migrations, starts the API, and starts the dashboard.

Open [http://127.0.0.1:3000](http://127.0.0.1:3000).

## Register a Sensor

```bash
./scripts/edge register
```

The helper stores the returned `sensor_id` and `sensor_token` in `.sensor.env`.

## Preview a Scan

Always preview first:

```bash
./scripts/edge preview 192.168.1.0/24
```

The preview prints the exact Nmap commands that would be executed.

## Submit a Scan

```bash
./scripts/edge scan 192.168.1.0/24
```

Add Wi-Fi observations when macOS exposes the local wireless scanner:

```bash
./scripts/edge scan 192.168.1.0/24 --wifi
```

## Generate an AI Report

Use the dashboard Reports page or run:

```bash
./scripts/edge report
```

After generation, open Reports in the dashboard and select the report. Use
`Download PDF` for the server-rendered A4 artifact, `Download HTML` for the
browser fallback, or `Copy Brief` for a text handoff. The PDF endpoint is
authenticated and workspace scoped:

```text
GET /api/v1/reports/{report_id}/export.pdf
```

Report period and metrics are frozen at generation time. Generate a fresh
report after an important scan instead of expecting an existing export to
change. The artifact includes normalized finding summaries, never evidence
objects, raw Nmap output, packet captures, or full scan logs.

## Test Everything

```bash
./scripts/edge test
```

This runs backend and agent tests, frontend tests, a production dashboard build, and a frontend dependency audit.

Before a tagged release or deployment, run the broader gate:

```bash
./scripts/edge release-check
```

It also checks the single Alembic head, Python/shell syntax, tracked credential
files, diff hygiene, and the full product test command. GitHub Actions repeats
the gate on PostgreSQL 16, checks model/schema drift, audits locked Python and
Node dependencies, and performs a real backup/restore drill.

## Health And Build Identity

- `/healthz` is process liveness and returns release/commit identity without
  touching PostgreSQL.
- `/readyz` performs a database round trip and requires the exact Alembic head.
- Settings > System Health is the authenticated operator view of environment,
  release, commit, schema, and AI provider.

Do not route pilot traffic to an API whose `/readyz` response is not `200`.

## Backup And Restore

Create and immediately verify an owner-only PostgreSQL custom archive:

```bash
./scripts/edge database backup
./scripts/edge database verify --input backups/secopsai-edge-<timestamp>.dump
```

For the hosted Render database, use the authenticated one-command workflow:

```bash
./scripts/edge cloud drift-check
./scripts/edge cloud backup
```

The drift check validates `render.yaml`, the live API build/start/health
contract, scheduler branch/commands/five-minute schedule, PostgreSQL status and
major version, and free-database expiry. It reads no environment variables or
secrets. Add `--json` for monitoring or `--fail-on-warning` when an expiring
free database should fail an automation gate.

The hosted backup command reads the database major from Render, pulls the
matching official PostgreSQL client image, temporarily adds only the current
public IP to the database allowlist, creates the archive, restores the original
allowlist, verifies required tables, and writes a SHA-256 manifest. It never
prints the connection URL. Docker and an authenticated Render CLI are required.
The normal local backup/restore command also uses a matching PostgreSQL Docker
client automatically when the host client major differs from the server.

Restore is destructive and requires both an explicit target URL and the exact
database name as a second confirmation:

```bash
./scripts/edge database restore \
  --input backups/secopsai-edge-<timestamp>.dump \
  --target-url postgresql://user:password@127.0.0.1:5432/secopsai_edge_restore \
  --confirm-database secopsai_edge_restore
```

Remote restores are refused unless `--allow-remote` is deliberately added.
For hosted production, prefer the provider's point-in-time restore into a new
database, validate `/readyz` and tenant counts, then switch the service. Never
practice a restore against the active production database.

Pilot target: daily backup, RPO 24 hours, RTO 4 hours. Paid production target:
managed point-in-time recovery, RPO 15 minutes or better, RTO 2 hours, and a
quarterly documented restore drill.

An archive is not considered recoverable until it has restored into a separate
database on the same PostgreSQL major and schema/table counts have been checked.
Never treat `pg_restore --list` alone as a restore test.

## Manage Approved Baselines

1. Open Assets and select an asset.
2. Add an approval note and choose `Approve Asset`, or choose `Accept Risk` beside an exact service.
3. Open Wi-Fi and choose `Trust BSSID` for an authorized access point.
4. Review or disable rules under Settings > Approved Baselines.

Baseline changes are audit logged. Disabling a rule reopens findings that were acknowledged by that rule. A trusted BSSID does not suppress weak/open-encryption findings.

## Audit And Support

Open Audit Log in the dashboard to review recent operator and sensor changes. Search by action, resource, identifier, or event details.

Create a redacted diagnostics bundle when a sensor needs support:

```bash
./scripts/edge support-bundle --cloud
```

The command records release, platform, dependency, API, worker-service, and recent worker-log status without copying credential files or printing tokens. The output is created with owner-only permissions. Review local paths and network ranges before sharing it.

The Core Integration panel defaults to `$HOME/secopsai-edge`, `$HOME/secopsai`,
and the hosted Core API URL. Update those fields once if the repositories or
API live elsewhere; the dashboard stores the preferences in that browser and
regenerates every copyable command without exposing credentials or
founder-specific paths publicly.

## Hosted API Workflow

After deploying the API to Render and the dashboard to Cloudflare Pages:

```bash
./scripts/edge onboard --cloud --api-url https://<your-render-api>.onrender.com \
  --enrollment-token <one-time-token> --install-service --start-service
./scripts/edge scan 192.168.1.0/24 --cloud
./scripts/edge report --cloud
```

Use the dashboard Settings page to connect to the hosted API with the dashboard admin email and
password. Invite additional operators from Users & Sessions; they choose their
own password from a one-time link. Enable authenticator-app MFA for privileged
operators and store the one-use recovery codes outside SecOpsAI. The admin token
remains available only for scheduler automation and emergency recovery. Create a
workspace-scoped Core export token from Settings for Edge-to-Core synchronization.
Create a separate **dashboard token** there for the canonical dashboard helper
and configure it as `SECOPSAI_EDGE_OPERATIONS_TOKEN`. Do not give the helper the
platform administrator token; the operations credential is read-only,
workspace-scoped, revocable, and limited to sites, sensors, schedules, and scan
jobs.

Settings recommends rotation when a scoped credential has 14 days remaining.
Choose **Rotate** to create an overlapping replacement, update the consumer,
verify one successful Core sync or dashboard refresh, and only then revoke the
previous short-ID credential. The replacement secret is shown once. The
canonical dashboard reads non-secret self-status and surfaces the same warning.

## Release And Rollback

1. Run `./scripts/edge release-check` and require green CI.
2. Create a verified database backup or provider recovery point.
3. Deploy the API; `scripts/render-start-api` applies migrations before Uvicorn.
4. Require `/readyz`, Settings > System Health, login, one read workflow, and
   one sensor heartbeat before declaring success.
5. Deploy the static dashboard and run the same smoke workflow.

Roll back application code only when it is compatible with the migrated schema.
If a schema rollback is unavoidable, stop writers, restore the pre-deploy backup
into a new database, point the previous API release at it, validate readiness,
then resume workers. Do not run blind Alembic downgrades on live customer data.

## Remote Scan Jobs

The hosted dashboard can queue a scan job, but the scan still runs locally.

Start the local worker:

```bash
./scripts/edge worker --cloud
```

For a single poll/execution cycle:

```bash
./scripts/edge worker --cloud --once
```

Flow:

1. Open the hosted dashboard.
2. Enter an authorized private CIDR in Scan Actions.
3. Click Queue Remote Scan.
4. Keep the local worker running.
5. Confirm the dashboard shows the sensor as online.
6. Refresh the dashboard as the job moves through queued, claimed, running, and completed.
7. Use Cancel for active jobs or Retry for failed/canceled jobs when needed.

Remote jobs are limited to RFC1918 IPv4 CIDRs with `/24` or narrower ranges. Worker heartbeats update last-seen, version, OS, hostname, state, and active job while both waiting and scanning; stale claimed/running jobs are recovered so they do not remain stuck forever. Sites shows this runtime context. A disabled sensor can be re-enabled there without rotating its token; rotate the token separately if credential exposure is suspected.

## Automatic Core Sync

Keep Core assets/findings current without manually exporting bundles:

```bash
SECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core export token: "))')"; export SECOPSAI_EDGE_CORE_TOKEN
./scripts/edge core sync-service install --cloud --core-root "$HOME/secopsai" --interval 300
unset SECOPSAI_EDGE_CORE_TOKEN
./scripts/edge core sync-service start
./scripts/edge core sync-service status
```

Use `run-now` after an important scan, and `logs` when the dashboard/Core inventory appears stale. The support bundle includes sync service status and recent redacted logs. Stopping or uninstalling this service does not stop the Edge scanner worker.

For a hosted Core API, choose **Install Hosted Sync** in Settings or run:

```bash
export SECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Edge Core export token: "))')"
export SECOPSAI_CORE_INGEST_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core ingest token: "))')"
./scripts/edge core sync-service install --cloud \
  --core-api-url https://<core-api>.onrender.com --interval 300
unset SECOPSAI_EDGE_CORE_TOKEN SECOPSAI_CORE_INGEST_TOKEN
./scripts/edge core sync-service start
```

This mode fetches only the normalized Edge export and sends it to the
organization-bound Core ingest endpoint. It does not need a local Core repo.

## Splunk HEC Export

Set these environment variables before starting the API:

```bash
export SPLUNK_HEC_ENABLED=true
export SPLUNK_HEC_URL="https://splunk.example.com:8088/services/collector/event"
export SPLUNK_HEC_TOKEN="<token>"
```

Only normalized findings and report summaries are exported.

## Safety Checklist

- Confirm you own or are authorized to scan the target network.
- Use private CIDRs only during the MVP.
- Start with `/24` or narrower.
- Keep administrator, sensor, enrollment, and Core export tokens out of screenshots and demos.
- Rotate sensor tokens before any customer pilot.
