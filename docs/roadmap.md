# SecOpsAI Edge Roadmap

This roadmap records product gaps, not historical aspirations. A capability is
listed as complete only when it has implementation and test evidence in
`docs/implementation-checkpoints.md`.

## Current Product Baseline - v0.2.7

The controlled-pilot baseline includes:

- Private-CIDR Nmap discovery with preview, limits, timeouts, and normalized
  asset/service observations.
- Local worker execution, heartbeat, remote scan jobs, stale-job recovery,
  cancel/retry, launchd, and systemd user services.
- Daily/weekly site schedules and an authenticated due-schedule runner.
- PostgreSQL migrations, organization/workspace isolation, user roles,
  workspace switching, audit logs, and revocable sessions.
- One-time sensor enrollment, scoped sensor tokens, scoped Core/dashboard
  integration credentials, expiry warnings, and overlap-safe rotation.
- Site, sensor, asset, Wi-Fi, baseline, finding, schedule, report,
  notification, audit, and system-health operator surfaces.
- Site-scoped approved assets, accepted services, and trusted BSSID baselines.
- Finding detail, notes, status/disposition workflow, assignment, bulk actions,
  and verify-by-rescan.
- Seven-day reports with frozen metrics, minimized AI payloads, client brief,
  authenticated PDF export, HTML fallback, and browser print.
- Email, Telegram, and signed-webhook notification endpoints.
- Redacted support bundles, backup/restore tooling, release gates, verified
  private release archives, Render API/PostgreSQL, Cloudflare dashboard,
  Render configuration drift checks, and matching-major hosted backups.
- Versioned Edge-to-Core graph/finding export and automated local Core sync.

## Immediate Pilot Hardening

These are the remaining highest-priority gaps before inviting an external pilot
without founder supervision:

1. **Hosted Core ingestion and one operator truth.** Deploy a server-side Core
   ingestion/helper service using the existing versioned bundle and scoped
   credentials. The main SecOpsAI dashboard must show Edge assets/findings
   without requiring a local Core repository.
2. **Paid pilot infrastructure.** A matching-major hosted export and isolated
   restore drill now protect the current demo data. Move Render API/PostgreSQL
   from free demo plans, enable managed backups or point-in-time recovery, and
   define an uptime target before accepting paid-pilot data.
3. **Browser end-to-end coverage.** Automate login, onboarding, enrollment,
   scan queue, schedule, finding triage, report generation/PDF download, and
   responsive accessibility checks against a disposable environment.
4. **Account recovery hardening.** Add password-reset delivery, optional MFA,
   invite acceptance, and explicit recovery-code/operator procedures.
5. **Notification delivery operations.** Persist delivery attempts, retries,
   terminal failure state, and operator-visible diagnostics for email,
   Telegram, and webhooks.

## Paid Pilot Readiness

- Fleet release visibility and a signed, staged sensor upgrade workflow with
  rollback.
- Sensor-offline alert evaluation independent of dashboard visits.
- Per-customer report branding, report retention policy, and export audit
  evidence.
- Support SLOs, escalation runbook, safe remote diagnostics, and pilot exit
  checklist.
- Explicit data-retention controls and customer-facing export/deletion flow.
- Independent penetration test and dependency/license review before broad
  customer access.

## SecOpsAI Platform Integration

- Make Core the canonical long-term finding, graph, triage, report, AI memory,
  and research store.
- Keep Edge responsible for local network reachability, raw scan handling,
  telemetry minimization, worker health, and authorized scan execution.
- Promote the canonical dashboard to the single operator surface; retain the
  Edge dashboard as a sensor administration/reference console until parity is
  proven.
- Add bidirectional workflow acknowledgements only after one-way ingestion and
  conflict ownership are operationally proven.
- Expose approved Core/Edge actions through OpenClaw with explicit approval for
  state-changing operations.

## Wireless Intelligence

- Validate TL-WN722N hardware/driver behavior separately on supported Linux and
  Raspberry Pi builds; do not advertise macOS monitor-mode support without
  measured evidence.
- Replace legacy macOS Wi-Fi collection dependencies with maintained adapters.
- Add a full rogue-AP review workflow, wireless observation history, and
  customer-approved SSID/BSSID policy.
- Keep passive capture opt-in, legally authorized, minimized, and outside the
  default SMB pilot.

## SecOpsAI Research

- Add a canonical `ResearchCase` lifecycle, evidence ledger, IOC store,
  disclosure state, confidence, and publication approvals in Core.
- Start with one ecosystem and a narrow brand/package watchlist; collect public
  metadata and artifacts, hash and unpack safely, then perform static analysis
  by default.
- Add typosquat/similarity scoring, publisher-history anomalies, install-hook
  detection, copied-metadata comparison, OSV/OpenSSF enrichment, and analyst
  review queues.
- Run dynamic analysis only in disposable, network-controlled sandboxes with
  no production credentials or access to third-party systems.
- Export reproducible research reports, IOCs, YARA/Sigma/Semgrep rules,
  responsible-disclosure packages, and reviewed drafts for
  `blog.secopsai.dev`.
- Feed confirmed campaigns back into SecOpsAI detections and customer
  watchlists without treating LLM output as evidence.

## SaaS/MSP Scale

Basic organizations, roles, workspace switching, and site scoping are already
present. Scale work still includes:

- Tenant-isolation adversarial tests, database row-level controls or equivalent
  defense in depth, and per-tenant encryption/retention decisions.
- MSP customer hierarchy, delegated administration, saved views, fleet health,
  and bulk policy rollout.
- SSO/SAML/OIDC, MFA policy, SCIM or controlled user provisioning, and stronger
  audit export.
- Usage metering, billing, entitlements, trial expiry, and support-plan limits.
- Regional hosting, data-processing terms, incident response, vulnerability
  disclosure, and compliance evidence appropriate to customer demand.

## Hardware Path

Continue Ethernet-first software pilots on MacBook, Raspberry Pi, and mini PC.
Build a repeatable Raspberry Pi image only after sensor upgrade/rollback,
headless recovery, disk durability, thermal behavior, and Wi-Fi adapter support
have passed soak testing. Custom enclosures, inventory purchasing, and custom
PCBs remain later-stage work.
