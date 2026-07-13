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

Password-reset requests are deliberately non-enumerating and always return the
same accepted response. One-time links are reconstructed from signed metadata;
the database retains only a keyed token hash, expiry, use state, and delivery
diagnostics. The token is placed in the URL fragment so it is not sent in the
initial HTTP request, then removed from the address bar by the dashboard. A
successful reset clears lockout state and revokes all existing user sessions.

Operator invitations use the same durable, one-time, keyed-hash token store.
New operators choose their own password; SecOpsAI never emails a temporary
password. Existing operators must prove their current password before an
invitation can add or reactivate workspace membership. Repeated invitation
password failures share the account lockout boundary and are audit logged.

Email requires `SMTP_HOST`. Telegram requires `TELEGRAM_BOT_TOKEN`.

## Credential Boundary

Dashboard auth should use a short-lived browser session created from a dashboard user login. The
server-side admin token remains available for scheduler automation and emergency recovery. Core
sync uses a separate expiring, revocable, workspace-scoped token restricted to `core:export`.
Sensor tokens are separate from dashboard auth and can be rotated from the Sites page.

Customer installs use random, HMAC-stored sensor enrollment tokens scoped to
one organization and one site. Enrollments expire after 30 minutes by default,
are consumed under a database row lock, and may be revoked before use. The
plaintext enrollment token appears only in the creation response and is never
stored in the dashboard or returned by list APIs. The installer persists only
the exchanged sensor token.

Core integration tokens are random and stored only as keyed HMAC digests. The
plaintext is returned once at creation. They cannot authenticate to general
dashboard, asset, scan, sensor, or administration endpoints. Revocation and
expiry are checked on every export, and last use is recorded for operator
review.

Dashboard passwords must contain at least 12 characters; a configured pilot or
production bootstrap password must contain at least 16. Repeated failures are
stored on the user record and lock the account temporarily after five attempts
by default. Lockouts and blocked attempts are audit logged. Mutation endpoints explicitly require an `owner` or `admin` role; viewers can inspect their assigned workspace but cannot change it. User sessions carry a server-validated generation number and active workspace claim. The API rechecks membership on every request, so logout, password reset/change, role change, membership disablement, or workspace removal immediately invalidates old access. Owner membership changes require an owner. The API prevents disabling or demoting the final active administrator in each workspace.

Dashboard bootstrap credentials create the configured first account only when
that email does not already exist. Application restarts never replace an
existing password, promote the account, or reactivate disabled membership.
After two owner recovery paths are confirmed, remove the bootstrap password
from hosted configuration.

Optional operator MFA uses RFC 6238 TOTP with a one-step clock window and
counter replay protection. TOTP secrets are encrypted with AES-GCM using the
operator ID as authenticated context and a dedicated
`SECOPSAI_MFA_ENCRYPTION_KEY`; recovery codes are stored only as keyed hashes
and consumed once. The dedicated key must be preserved across deploys and
backups. It must not silently inherit or rotate with the dashboard session
token secret.

Replacing an enrolled authenticator requires disabling the existing factor
with both the current password and a valid TOTP/recovery code. When both factor
and recovery codes are lost, a different workspace owner may perform an
audited MFA reset for that operator. Self-reset is rejected, and the reset
revokes all existing sessions.

Every site belongs to one organization. Lists, guessed resource IDs, filters, report downloads,
notification history, audit history, and Core export are all server-filtered to the authenticated
organization; a workspace selector is not treated as a security boundary by itself. Existing data
is backfilled into `Default Workspace` during migration `0009_organizations`.

## Baseline Boundary

Approved baselines are scoped to one site and a stable entity identifier. The API rejects empty or broad matchers, restricts each baseline kind to compatible finding types, records changes in the audit log, and reopens baseline-acknowledged findings when a rule is disabled. Trusting a BSSID does not approve weak or open encryption unless an operator deliberately creates that separate policy through the API.

## Production Configuration Boundary

`SECOPSAI_ENVIRONMENT=pilot` and `SECOPSAI_ENVIRONMENT=production` fail startup
when administrator/session/MFA or webhook secrets are short/default, automatic
schema creation is enabled, or localhost CORS origins remain. Database schema
is managed only by Alembic.
Backups are PostgreSQL custom archives created with owner-only permissions;
restore requires an exact database-name confirmation and refuses remote targets
unless the operator explicitly opts in. A matching PostgreSQL Docker client is
selected when the host client major differs from the database. Hosted Render
backup temporarily allowlists only the operator's current IP and restores the
original allowlist before verification; connection URLs are passed directly to
the private backup process and are never printed. Credential files and backup
archives are excluded from Git.

Sensor releases are built from committed Git content, version-matched across
API/agent/dashboard, and published with SHA-256 checksums. Public repositories
also receive GitHub build-provenance attestations; GitHub does not offer that
feature to user-owned private repositories. Private pilot installers use an
authenticated GitHub CLI and require repository collaborator access; public
releases may use HTTPS directly. The bootstrap verifies the checksum
before extraction, refuses to overwrite an installation without `--upgrade`,
preserves credentials, and rolls back the directory swap when installation
fails. Release archives exclude ignored credentials, virtual environments,
Node dependencies, and generated build output.

Workspace integration credentials are scope-separated. `core:export` can read
only the normalized Core bundle. `operations:read` can read only sites,
sensors, scan schedules, and scan jobs for its workspace. Neither token can
mutate Edge state or access assets, findings, reports, users, audit logs, or
another workspace. The canonical dashboard helper must use
`SECOPSAI_EDGE_OPERATIONS_TOKEN`; the legacy administrator-token fallback is a
temporary migration path and must not be exposed to browser configuration.

An integration credential may read only its own identifier, scopes, state,
expiry, and last-use metadata. Rotation returns a new secret once and keeps the
previous credential active so the consumer can be verified before revocation.
This overlap is deliberate; operators must revoke the previous credential
after a successful handover.

Hosted Core ingestion has a second, independent credential boundary. The Edge
bridge reads with a workspace-scoped `core:export` token and writes with a Core
ingest token bound to the same organization ID. Both are held in an owner-only
service credential file and omitted from process arguments, logs, dashboard
storage, and support bundles. The bridge refuses redirects, non-loopback plain
HTTP, oversized responses, and unconfirmed imports. Core independently rejects
raw scanner fields, oversized graph contracts, duplicate identifiers, and
cross-organization bundles; its read credential cannot ingest data.
