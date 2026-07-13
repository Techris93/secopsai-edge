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

Notifications export normalized event summaries. Webhook targets receive event type, title, summary, severity/type when applicable, and minimized evidence. Every webhook is HMAC-SHA256 signed over its timestamp and exact request body. Delivery records retain retry metadata and minimized payload server-side; the dashboard/API delivery history deliberately excludes payload bodies.

Email requires `SMTP_HOST`. Telegram requires `TELEGRAM_BOT_TOKEN`.

## Credential Boundary

Dashboard auth should use a short-lived browser session created from a dashboard user login. The
server-side admin token remains available for automation, cron, Core sync, and emergency recovery.
Sensor tokens are separate from dashboard auth and can be rotated from the Sites page.

Customer installs use random, HMAC-stored sensor enrollment tokens scoped to
one organization and one site. Enrollments expire after 30 minutes by default,
are consumed under a database row lock, and may be revoked before use. The
plaintext enrollment token appears only in the creation response and is never
stored in the dashboard or returned by list APIs. The installer persists only
the exchanged sensor token.

Dashboard bootstrap passwords must contain at least 12 characters. Repeated failures are stored on the user record and lock the account temporarily after five attempts by default. Lockouts and blocked attempts are audit logged. Mutation endpoints explicitly require an `owner` or `admin` role; viewers can inspect their assigned workspace but cannot change it. User sessions carry a server-validated generation number and active workspace claim. The API rechecks membership on every request, so logout, password reset/change, role change, membership disablement, or workspace removal immediately invalidates old access. Owner membership changes require an owner. The API prevents disabling or demoting the final active administrator in each workspace.

Every site belongs to one organization. Lists, guessed resource IDs, filters, report downloads,
notification history, audit history, and Core export are all server-filtered to the authenticated
organization; a workspace selector is not treated as a security boundary by itself. Existing data
is backfilled into `Default Workspace` during migration `0009_organizations`.

## Baseline Boundary

Approved baselines are scoped to one site and a stable entity identifier. The API rejects empty or broad matchers, restricts each baseline kind to compatible finding types, records changes in the audit log, and reopens baseline-acknowledged findings when a rule is disabled. Trusting a BSSID does not approve weak or open encryption unless an operator deliberately creates that separate policy through the API.

## Production Configuration Boundary

`SECOPSAI_ENVIRONMENT=production` fails startup when administrator/session or
webhook secrets are short/default, automatic schema creation is enabled, or
localhost CORS origins remain. Database schema is managed only by Alembic.
Backups are PostgreSQL custom archives created with owner-only permissions;
restore requires an exact database-name confirmation and refuses remote targets
unless the operator explicitly opts in. Credential files and backup archives
are excluded from Git.
