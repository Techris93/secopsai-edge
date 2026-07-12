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

## Test Everything

```bash
./scripts/edge test
```

This runs backend and agent tests, frontend tests, a production dashboard build, and a frontend dependency audit.

## Manage Approved Baselines

1. Open Assets and select an asset.
2. Add an approval note and choose `Approve Asset`, or choose `Accept Risk` beside an exact service.
3. Open Wi-Fi and choose `Trust BSSID` for an authorized access point.
4. Review or disable rules under Settings > Approved Baselines.

Baseline changes are audit logged. Disabling a rule reopens findings that were acknowledged by that rule. A trusted BSSID does not suppress weak/open-encryption findings.

## Hosted API Workflow

After deploying the API to Render and the dashboard to Cloudflare Pages:

```bash
./scripts/edge cloud configure https://<your-render-api>.onrender.com
./scripts/edge cloud register
./scripts/edge scan 192.168.1.0/24 --cloud
./scripts/edge report --cloud
```

Use the dashboard Settings page to connect to the hosted API with the dashboard admin email and
password. The admin token remains available only for automation, cron, Core sync, and recovery.

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

Remote jobs are limited to RFC1918 IPv4 CIDRs with `/24` or narrower ranges. Worker heartbeats update the sensor last-seen timestamp; stale claimed/running jobs are recovered so they do not remain stuck forever.

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
- Keep `SECOPSAI_ADMIN_TOKEN` and sensor tokens out of screenshots and demos.
- Rotate sensor tokens before any customer pilot.
