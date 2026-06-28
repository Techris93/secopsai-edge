# SecOpsAI Edge Pilot Guide

## What It Does

SecOpsAI Edge discovers internal network assets, records service exposure, monitors Wi-Fi inventory when available, detects risky changes, and generates AI-assisted reports from normalized findings.

## What It Does Not Do

- It does not scan public internet ranges by default.
- It does not send raw Nmap output, packet captures, or raw scan logs to AI providers.
- It does not replace endpoint detection or a full SIEM.
- It does not fix issues automatically in this pilot version.

## Pilot Workflow

1. Create or select a site in the dashboard.
2. Install and onboard the local sensor.
3. Confirm the worker is online.
4. Queue a scan or configure a schedule.
5. Review Assets, Wi-Fi, and Findings.
6. Add notes and mark findings acknowledged/resolved/false positive.
7. Generate a report.
8. Open the report detail page, copy the executive summary, print, or download HTML.
9. Configure webhook/email/Telegram notifications.
10. Sync Edge findings into SecOpsAI Core when needed.

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

## Recovery

Rotate a sensor token from the Sites page when credentials are lost or leaked. After rotating, update `.cloud-sensor.env` on the sensor and restart the worker.

Disable retired sensors from the Sites page. Queued jobs for disabled sensors are canceled.
