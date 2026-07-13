# SecOpsAI Edge Pilot Guide

## What It Does

SecOpsAI Edge discovers internal network assets, records service exposure, monitors Wi-Fi inventory when available, detects risky changes, and generates AI-assisted reports from normalized findings.

## What It Does Not Do

- It does not scan public internet ranges by default.
- It does not send raw Nmap output, packet captures, or raw scan logs to AI providers.
- It does not replace endpoint detection or a full SIEM.
- It does not fix issues automatically in this pilot version.

## Pilot Workflow

1. Connect the dashboard to the API from Settings and confirm it shows `Live API data`.
2. Create or select a site in the dashboard.
3. Click `Enroll sensor` for the target site, copy the one-time installer, and
   run it on the authorized MacBook/Raspberry Pi.
4. Confirm the worker is online.
5. Queue a scan or configure a schedule.
6. Review Assets, Wi-Fi, and Findings.
7. Add notes and mark findings acknowledged/resolved/false positive.
8. Approve known assets, accepted services, and trusted BSSIDs to establish the site baseline.
9. Generate a report.
10. Open the report detail page, verify the frozen reporting period and metrics, then copy the executive summary/client brief or download the client-ready PDF.
11. Configure webhook/email/Telegram notifications.
12. Install automatic Edge-to-Core sync, choosing local import or hosted Core
    push, and confirm its status/logs.
13. Confirm important operator actions appear in Audit Log.

## Establish The Baseline

Use Asset Detail to approve an owned device or accept an intentionally exposed service. Use Wi-Fi to trust an exact BSSID. Active rules are visible and reversible under Settings > Approved Baselines.

- Approving an asset acknowledges `new_device` and `vendor_unknown`; missing-device changes remain visible.
- Accepting a service applies only to that asset, port, and protocol.
- Trusting a BSSID acknowledges duplicate-SSID noise; weak/open encryption remains a finding.
- Disabling a baseline reopens findings that were acknowledged by that rule.

## Dashboard Data States

- `Live API data`: the dashboard is connected to the configured API and is showing real pilot telemetry.
- `API not connected`: the dashboard cannot read pilot telemetry yet. Open Settings, create an API session, and confirm the API URL is correct.
- `Demo data only`: sample telemetry is visible only when demo mode is explicitly enabled with `NEXT_PUBLIC_SECOPSAI_DEMO_MODE=true`. Do not use demo mode for customer pilots.

## Required Permission

The pilot operator must have permission to scan the target LAN. Discovery is limited to RFC1918 private IPv4 networks and `/24` or smaller CIDRs for dashboard-queued scans.

## Data Collected

- IP address
- MAC address when visible
- hostname when visible
- vendor
- OS guess
- open service metadata
- Wi-Fi SSID/BSSID/channel/signal/encryption when available
- findings, notes, schedules, reports, and audit logs

## Data Not Sent To AI

- raw Nmap output
- packet captures
- full scan logs
- raw telemetry history

Sensitive evidence fields such as MAC address, BSSID, and hostnames are redacted in report payloads.

## Share A Report

Generate the report only after the latest scheduled or manual scan completes.
The report captures a seven-day period, current asset totals, new devices,
risky services, Wi-Fi risks, finding status counts, completed scans, severity,
recommended actions, and the normalized findings included at that moment.

Use `Download PDF` for the client/boss artifact. Use `Download HTML` for an
editable browser copy, `Print` for the operating system print dialog, or `Copy
Brief` for a short handoff. Raw Nmap output, packet data, scan logs, and finding
evidence objects are excluded from the PDF.

## Recovery

Rotate a sensor token from the Sites page when credentials are lost or leaked. After rotating, update `.cloud-sensor.env` on the sensor and restart the worker.

Disable retired sensors from the Sites page. Queued jobs for disabled sensors are canceled.

New sensor installs use 30-minute, single-use enrollment tokens created in the
active workspace. Revoke an unused enrollment from Sites if the command was
sent to the wrong person. Enrollment secrets are never recoverable from the API
after the creation response; create a replacement instead.

For a support-safe operational snapshot, run `./scripts/edge support-bundle --cloud` or copy the command from Settings. Review the generated file before sharing because local paths and authorized network ranges can remain visible.
