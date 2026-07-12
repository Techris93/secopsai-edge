# Security Boundaries

## Scanning Boundary

Dashboard-queued scans accept private IPv4 CIDRs only:

- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`

Remote scan jobs are limited to `/24` or narrower targets. The API rejects public ranges.

## AI Boundary

AI reports receive normalized findings, not raw scanner logs. Evidence redaction removes sensitive identifiers such as MAC address, BSSID, and hostname before provider submission.

If `AI_PROVIDER=openai` or `AI_PROVIDER=http` fails, report generation falls back to deterministic mock output and records the provider error in the report content.

## Sensor Boundary

The hosted API cannot see a private office LAN. The local worker must run on the MacBook, Raspberry Pi, or mini PC inside the authorized network.

## Notification Boundary

Notifications export normalized event summaries. Webhook targets receive event type, title, summary, severity/type when applicable, and minimized evidence.

Email requires `SMTP_HOST`. Telegram requires `TELEGRAM_BOT_TOKEN`.

## Credential Boundary

Dashboard auth should use a short-lived browser session created from a dashboard user login. The
server-side admin token remains available for automation, cron, Core sync, and emergency recovery.
Sensor tokens are separate from dashboard auth and can be rotated from the Sites page.
