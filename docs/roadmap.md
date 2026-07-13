# SecOpsAI Edge Roadmap

This roadmap records product gaps, not historical aspirations. A capability is
listed as complete only when it has implementation and test evidence in
`docs/implementation-checkpoints.md`.

## Current Product Baseline - v0.3.0

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

1. **Paid pilot infrastructure.** A matching-major hosted export and isolated
   restore drill now protect the current demo data. Move Render API/PostgreSQL
   from free demo plans, enable managed backups or point-in-time recovery, and
   define an uptime target before accepting paid-pilot data.
2. **Browser end-to-end coverage.** Desktop/mobile Chromium now protects login,
   password recovery, scan queueing, finding triage, schedule creation, and
   report generation against a disposable API contract. Invitation acceptance
   and MFA login are also covered; onboarding enrollment, PDF download,
   keyboard paths, and automated accessibility checks remain.
3. **Account access activation.** Invitation acceptance, password recovery,
   TOTP MFA, one-use recovery codes, and owner-assisted reset are implemented.
   Configure an approved SMTP provider, enroll a second owner, and exercise the
   full recovery path before inviting an external operator.
4. **Notification delivery operations.** Delivery attempts, retries, terminal
   failure state, and operator-visible diagnostics are implemented for email,
   Telegram, webhooks, invitation, and password-reset email. Exercise the
   selected real provider and alert destinations.
5. **Pilot support and data lifecycle.** Define retention/deletion controls,
   uptime/support targets, escalation ownership, and a customer-facing pilot
   exit/export procedure.

## Controlled Pilot Completion Sequence

The checkpoint ledger is complete through `036`. The remaining controlled-pilot
sequence is deliberately bounded and should be completed in this order:

1. **Checkpoint 037 - Accessibility and browser completion.** Automated WCAG
   checks plus enrollment, PDF download, keyboard, responsive, empty, error,
   and degraded-state workflows against the production build.
2. **Checkpoint 038 - Durable pilot infrastructure and recovery proof.** Paid
   database/API decision, managed backups or equivalent, restore drill,
   retention/deletion controls, uptime target, and operator recovery exercise.
3. **Checkpoint 039 - Research and wireless operational boundary.** First
   narrowly scoped package-research workflow, reproducible evidence export,
   Linux/Raspberry Pi wireless validation, and explicit unsupported-platform
   messaging.
4. **Checkpoint 040 - External pilot acceptance.** Fresh-machine installation,
   seven-day soak, schedule/notification/offline-sensor exercises, support SLO,
   uninstall, and pilot exit checklist.
5. **Checkpoint 041 - Controlled-pilot release closeout.** Exact-build deploy,
   release artifacts, public docs alignment, final security review, known-risk
   register, and a signed pilot go/no-go record.

Commercial SaaS/MSP, billing, broad fleet automation, appliance imaging, and
multi-ecosystem research automation remain subsequent product horizons rather
than hidden requirements of the controlled-pilot release.

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
