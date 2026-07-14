# SecOpsAI Edge Roadmap

This roadmap records product gaps, not historical aspirations. A capability is
listed as complete only when it has implementation and test evidence in
`docs/implementation-checkpoints.md`.

## Current Product Baseline - v0.3.8

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
- Hosted Core API deployment and normalized Edge bundle ingestion are verified
  at `https://secopsai-core-api.onrender.com`; the hosted operator workspace
  is populated without raw scanner telemetry. See checkpoint `055`.
- Unified Core console visibility for Edge sync freshness, including current,
  stale, and never-synced states.
- OpenClaw read-only Edge operator checks for local worker status and safe
  private-CIDR scan previews, with no direct scan or service mutation.
- OpenClaw approval-gated Edge scan requests that create a Core approval,
  validate the target in Core and Edge, and queue work for the local worker
  without exposing credentials or raw scanner output.
- OpenClaw approval-gated Edge report generation and worker start/stop actions,
  constrained to allowlisted helper arguments and recorded in Core sessions.
- CLI sensor-token recovery with atomic owner-only credential replacement and
  a documented worker restart path.
- OpenClaw research tools aligned with all twelve ecosystems supported by Core,
  including NuGet, Maven, Go, crates.io, Open VSX, and RubyGems.
- Workspace retention policies, normalized customer export, owner-confirmed
  site deletion, and non-secret hosted availability evidence.

## Immediate Pilot Hardening

These are the remaining highest-priority gaps before inviting an external pilot
without founder supervision:

1. **Paid pilot infrastructure activation.** A matching-major hosted export,
   isolated restore drill, lifecycle controls, and 99.5% internal readiness
   target now protect the demo. The account owner must still move Render
   API/PostgreSQL from free demo plans and perform a paid-database PITR drill
   before accepting external data.
2. **Browser and accessibility operations.** Desktop/mobile Chromium now
   protects login, password recovery, invitation acceptance, MFA, scan queueing,
   finding triage, schedule creation, report generation, sensor enrollment, PDF
   download, keyboard paths, responsive layouts, and automated WCAG checks.
   Complete a manual VoiceOver/NVDA review before broad commercial use.
3. **Account access activation.** Invitation acceptance, password recovery,
   TOTP MFA, one-use recovery codes, and owner-assisted reset are implemented.
   Configure an approved SMTP provider, enroll a second owner, and exercise the
   full recovery path before inviting an external operator.
4. **Notification delivery operations.** Delivery attempts, retries, terminal
   failure state, and operator-visible diagnostics are implemented for email,
   Telegram, webhooks, invitation, and password-reset email. Exercise the
   selected real provider and alert destinations.
5. **Pilot support and data lifecycle.** Retention/deletion controls,
   uptime/support targets, escalation ownership, and a customer-facing pilot
   exit/export procedure are implemented and documented. Exercise them with a
   second real operator during checkpoint `040`.

## Controlled Pilot Completion Sequence

Implementation checkpoints are complete through `054`. The remaining work is
external operator acceptance, not untracked feature development:

1. **Checkpoint 040 - External pilot acceptance.** Complete fresh-machine
   installation, seven-day soak, schedule/notification/offline-sensor
   exercises, support SLO, paid Render/PITR activation, two-owner recovery,
   uninstall, and the pilot exit checklist.
2. **Checkpoint 041 - Release closeout.** The exact verified `v0.3.4` build
   closeout was superseded by the verified `v0.3.5` release in checkpoint 042.
3. **Checkpoint 042 - AI report cost guardrail and release evidence.** The
   report cooldown, operator visibility, release archive, Render identity, and
   Edge Pages deployment are verified. Attach the external evidence and signed
   pilot go/no-go record before calling the controlled pilot customer-ready.
4. **Checkpoint 043 - Cross-product sync freshness.** Core, Dashboard, and
   OpenClaw now share the same normalized Edge-to-Core freshness signal.
5. **Checkpoint 044 - Safe OpenClaw Edge operator tools.** OpenClaw can check
   the local worker and preview an authorized private CIDR without executing or
   uploading a scan.
6. **Checkpoint 045 - Research ecosystem contract alignment.** OpenClaw's
   package-research schemas now expose the same twelve ecosystem choices as
   Core, including NuGet-style package investigations.
7. **Checkpoint 046 - Approval-gated Edge scan actions.** OpenClaw can create
   a Core session and pending approval for an authorized scan. Applying the
   approval invokes only the structured Edge queue helper; direct Nmap and
   worker-service mutation remain outside the plugin.
8. **Checkpoint 047 - Approval-gated Edge operations.** Report generation and
   worker start/stop are now approval-backed Core session actions with no raw
   helper output or credentials crossing into Core.
9. **Checkpoint 048 - Sensor credential recovery CLI.** Sensor hosts can rotate
   a hosted sensor credential and restart the worker without manual secret-file
   editing or exposing the replacement token in command output.
10. **Checkpoint 050 - Hosted health failure diagnostics.** Hosted API and
    dashboard failures now produce stable non-secret error codes, and the
    verified `v0.3.7` release records the release-gate evidence; the subsequent
    `v0.3.8` release also verifies the corrected tag publication workflow.
11. **Checkpoint 052 - Authenticated pilot evidence.** The acceptance preflight
    can require an operator credential and verify authenticated identity,
    system status, onboarding, sites, sensors, schedules, findings, and reports
    without recording the token or response bodies.
12. **Checkpoint 054 - Hosted operator evidence.** The live Render API and
    authenticated operator surfaces were verified for `v0.3.8`; Cloudflare
    Pages and the remaining fresh-host/soak/provider exercises remain explicitly
    pending.
13. **Checkpoint 055 - Hosted Core API activation.** Core PR `#44` is merged,
    the hosted Core service accepts the versioned Edge bundle, and the
    authenticated workspace exposes normalized assets/findings. Independent
    dashboard aggregation and the remaining external pilot evidence gates are
    still pending.

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
  state-changing operations. Worker status, scan preview, approval-gated scan
  queueing, report generation, and worker start/stop are implemented. Token
  rotation remains a separate administrative workflow.

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
