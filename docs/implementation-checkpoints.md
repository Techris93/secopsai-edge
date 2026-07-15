# SecOpsAI Edge Implementation Checkpoints

This file is the resume ledger for turning SecOpsAI Edge from a technical MVP
into a pilot-ready SecOpsAI sensor module. Update it at the end of every
implementation batch.

## Current Strategy

SecOpsAI Edge should become the network discovery and sensor module for the
main SecOpsAI product:

- Main product: https://secopsai.dev
- Research and advisories: https://blog.secopsai.dev
- Operator docs: https://docs.secopsai.dev
- Edge module: local LAN discovery, Wi-Fi inventory, sensor worker, scan jobs,
  safe telemetry minimization, and Edge-to-Core export.

Core should own long-term graph context, canonical findings, triage, reports,
research intelligence, and AI memory. Edge should continue to own local
collection and worker execution.

## Priority Order

1. Make the pilot experience truthful and recoverable.
2. Make the Edge/Core story feel like one SecOpsAI product.
3. Harden auth, operations, reporting, and release hygiene.
4. Build the research module and public research workflow.
5. Add SaaS/MSP and hardware-appliance capabilities after pilot workflows work.

## Checkpoint 001 - Pilot Hardening Foundation

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Scope:

- Add this checkpoint ledger.
- Remove ambiguous dashboard demo fallback behavior.
- Add explicit live, demo, and blocked connection states to the dashboard.
- Align Edge docs with the public SecOpsAI surfaces.
- Run focused validation before closing the checkpoint.

Completed changes:

- Added `DashboardDataMode` with `live`, `demo`, and `blocked` states in
  `web/src/lib/api.ts`.
- Changed dashboard data loading so sample data is shown only when
  `NEXT_PUBLIC_SECOPSAI_DEMO_MODE=true`.
- Updated `LiveState` and the Overview, Assets, Wi-Fi, Findings, Reports,
  Onboarding, Schedules, and Sites pages to display the explicit data state.
- Updated `README.md`, `docs/pilot-guide.md`, and
  `docs/render-cloudflare-deploy.md` with the Edge module role, public
  SecOpsAI surfaces, and dashboard data-state rules.

Validation:

- `npm test -- --run` from `web/`: 3 test files passed, 5 tests passed.
- `npm run build` from `web/`: static Next.js production build passed.
- `./scripts/edge test`: 31 backend/agent tests passed, 5 frontend tests
  passed, production dashboard build passed, npm audit found 0 vulnerabilities.

Known risks at checkpoint close:

- Main SecOpsAI was still a dirty worktree at this checkpoint; Checkpoint 005
  later isolated the generated content and committed Core integration cleanly.
- The dashboard still needs stronger empty/error panels for blocked API state;
  this checkpoint fixed truthfulness before redesigning every state surface.
- Existing FastAPI startup event deprecation warnings remain and should be
  handled in a later backend hygiene pass.

Deferred at this checkpoint:

- Main SecOpsAI cleanup and integration work, completed in Checkpoint 005.
- OpenClaw plugin.
- Cloud deployment.
- Billing, SaaS multi-tenancy, or hardware image work.

Next checkpoint should start with:

1. Edge asset detail and change timeline.
2. Branded report export/download polish.
3. Stronger blocked/empty/error dashboard panels.
4. Core repo hygiene and Edge/Core sync automation review.
5. Production auth design and implementation.

## Checkpoint 002 - Asset Detail and Change Timeline

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Scope:

- Add an asset detail API that exposes normalized observations, related findings,
  and a computed timeline without raw scan logs.
- Add dashboard navigation from Assets to asset detail.
- Add an asset detail dashboard screen for identity, services, findings, timeline,
  and recent observations.
- Add tests for the asset detail API privacy boundary and authorization.

Validation to run before closing:

- Focused API tests for asset detail.
- Frontend tests and production build.
- `./scripts/edge test`.

Completed changes:

- Added `GET /api/v1/assets/{asset_id}` with normalized asset observations,
  related findings, and computed timeline events.
- Added asset detail schemas for observations, timeline events, and detail
  response payloads.
- Added backend tests confirming asset detail requires admin auth and does not
  expose raw scan payload fields.
- Added `getAsset()` and asset-detail frontend types.
- Added a live-only Detail action from the Assets table.
- Added `/assets/detail` dashboard route with identity, exposed services,
  related findings, change timeline, and recent observation views.

Validation:

- `PYTHONPATH=api:agent .venv/bin/python -m pytest tests/api/test_asset_detail.py`:
  2 tests passed.
- `npm test -- --run` from `web/`: 3 test files passed, 5 tests passed.
- `npm run build` from `web/`: static Next.js production build passed and
  included `/assets/detail`.
- `./scripts/edge test`: 33 backend/agent tests passed, 5 frontend tests
  passed, production dashboard build passed, npm audit found 0 vulnerabilities.

Known risks:

- Timeline events are computed from current normalized rows, not a dedicated
  immutable change-event table yet.
- Service removal history is not visible until the backend stores historical
  service transitions instead of only current service state.
- Asset detail is currently reachable by query parameter, matching existing
  finding/report detail pages; route params can be cleaned up in a UI routing
  polish pass.

## Checkpoint 003 - Report Export Polish

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Scope:

- Add a backend-rendered branded HTML report export endpoint.
- Update the report detail dashboard to download the backend export.
- Add a richer client-brief copy action for customer/MSP sharing.
- Add tests for report export authorization and content.

Validation to run before closing:

- Focused API tests for report HTML export.
- Frontend tests and production build.
- `./scripts/edge test`.

Completed changes:

- Added authenticated `GET /api/v1/reports/{report_id}/export.html`.
- Added server-side branded HTML report rendering with escaped report fields,
  site metadata, risk, provider/model, recommended actions, and included findings.
- Added report export filename generation and reused a report 404 helper.
- Added API test coverage for export authorization, branded content, and raw
  scan-content minimization.
- Updated the dashboard report detail page to download the backend-rendered
  report export.
- Added `Copy Brief` for a richer customer/MSP handoff summary.
- Updated pilot workflow docs to match the report detail actions.

Validation:

- `PYTHONPATH=api:agent .venv/bin/python -m pytest tests/api/test_pilot_mvp.py::test_report_html_export_requires_admin_and_returns_branded_report`:
  1 test passed.
- `npm test -- --run` from `web/`: 3 test files passed, 5 tests passed.
- `npm run build` from `web/`: static Next.js production build passed.
- `./scripts/edge test`: 34 backend/agent tests passed, 5 frontend tests
  passed, production dashboard build passed, npm audit found 0 vulnerabilities.

Known risks:

- Export is polished HTML/print-to-PDF rather than generated PDF bytes.
- Report content depends on the existing report JSON structure; future report
  schema changes should keep export tests updated.
- Email delivery of reports is still a later notification workflow, not part of
  this checkpoint.

## Checkpoint 004 - Dashboard Blocked and Demo State Panels

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Scope:

- Add a reusable dashboard data-state panel.
- Show a clear operator next step when the API/session is blocked.
- Show an explicit demo-mode note when sample data is intentionally enabled.
- Apply the panel to the main operator screens that load dashboard data.

Validation to run before closing:

- Frontend tests and production build.
- `./scripts/edge test`.

Completed changes:

- Added reusable `DataStatePanel` for blocked API/session and explicit demo
  mode states.
- Added blocked/demo panels to Overview, Assets, Wi-Fi, Findings, Reports,
  Onboarding, Schedules, and Sites.
- Kept Settings as the recovery screen because it already contains the API
  connection workflow.

Validation:

- `npm test -- --run` from `web/`: 3 test files passed, 5 tests passed.
- `npm run build` from `web/`: static Next.js production build passed.
- `./scripts/edge test`: 34 backend/agent tests passed, 5 frontend tests
  passed, production dashboard build passed, npm audit found 0 vulnerabilities.

Known risks:

- Empty states inside individual tables/lists are still basic and should be
  redesigned in a broader UI system pass.
- Notification settings use the Settings recovery context rather than their own
  data-state panel.

## Checkpoint 005 - Core Worktree Hygiene and One-Step Sync

Status: complete

Branches:

- Edge repo: `codex/pilot-hardening-foundation`
- Core repo: `codex/core-edge-hygiene`

Scope:

- Treat the Core Edge integration files as owned work and leave unrelated
  generated blog/news files untouched.
- Add a one-step Edge helper that exports an Edge bundle and imports it into
  SecOpsAI Core.
- Add dashboard and docs buttons/commands for the one-step sync path.
- Validate Edge and focused Core integration tests.

Core worktree result:

- `/Users/chrixchange/secopsai` is clean on `codex/core-edge-hygiene`.
- Generated blog/news output is isolated on `codex/blog-news-generated-review`
  for an explicit content-release decision.

Validation to run before closing:

- `bash -n scripts/edge`
- focused Edge dashboard tests/build
- focused Core Edge integration tests
- `./scripts/edge test`

Completed changes:

- Created Core branch `codex/core-edge-hygiene` so Edge/Core integration work
  is no longer floating only on Core `main`.
- Committed the Core integration bundle as
  `b202c9c Integrate SecOpsAI Edge graph sync into Core`.
- Moved unrelated generated blog/news output to
  `codex/blog-news-generated-review` and committed it separately as
  `229f332 Isolate generated blog news batch for review`.
- Added `./scripts/edge core sync`, which exports the Edge Core bundle and
  imports it into SecOpsAI Core in one command.
- Added `--core-root`, `--output`, `--db-path`, and `--cloud` options for the
  one-step sync wrapper.
- Added a dashboard `Copy One-Step Sync` button in the Core integration panel.
- Updated Edge README, Edge Core integration docs, and demo script to prefer
  one-step sync.
- Updated Core `docs/edge-integration.md` with the Edge-side one-step sync path.
- Kept unrelated Core blog/news generated files untouched.

Validation:

- `bash -n scripts/edge`: passed.
- `npm test -- --run CoreIntegrationPanel` from `web/`: 1 test file passed,
  2 tests passed.
- `.venv/bin/python -m pytest tests/test_edge_integration.py` from Core:
  4 tests passed.
- `./scripts/edge test`: 34 backend/agent tests passed, 5 frontend tests
  passed, production dashboard build passed, npm audit found 0 vulnerabilities.
- `.venv/bin/python -m pytest tests` from Core: 221 tests passed.
- `.venv/bin/python -m pytest tests/test_blog.py` from Core blog review branch:
  26 tests passed.

Automation rule going forward:

- Repeated multi-command product workflows should become script commands first.
- Hosted/API-safe actions should become real dashboard buttons.
- Local machine actions that a browser cannot safely run should become
  copyable dashboard command buttons with exact paths and arguments.
- Git cleanup should split unrelated work into separate branches/commits by
  product area before continuing implementation.

Known risks:

- Generated blog/news content is isolated on its own branch but still needs a
  human content/release decision before publishing.
- The one-step sync imports into local Core; hosted Core ingestion remains a
  later API milestone.
- Core Edge integration is committed locally but not pushed.

## Checkpoint 006 - Production Auth Foundation

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Scope:

- Add real dashboard user login while preserving admin-token compatibility for
  scripts, cron, and existing deployments.
- Support environment-driven bootstrap of an initial dashboard admin user.
- Update the dashboard Settings connection panel to prefer email/password login
  and move the admin token path into a legacy/automation fallback.
- Add focused API and frontend tests.

Files changed:

- `.env.example`
- `render.yaml`
- `api/secopsai_api/config.py`
- `api/secopsai_api/main.py`
- `api/secopsai_api/schemas.py`
- `api/secopsai_api/security.py`
- `tests/api/test_auth.py`
- `web/src/components/ApiConnectionPanel.tsx`
- `web/src/components/ApiConnectionPanel.test.tsx`
- `web/src/lib/api.ts`
- `web/src/lib/types.ts`
- `docs/render-cloudflare-deploy.md`
- `docs/runbook.md`
- `docs/security-boundaries.md`
- `docs/implementation-checkpoints.md`

Validation:

- `PYTHONPATH=api:agent .venv/bin/python -m pytest tests/api/test_auth.py tests/api/test_security.py`
  passed with 7 tests.
- `cd web && npm test -- --run ApiConnectionPanel` passed with 2 tests.
- `python3 -m py_compile scripts/render-run-due-schedules` passed.
- `bash -n scripts/edge` passed.
- `./scripts/edge test` passed with 39 backend/agent tests, 7 frontend
  tests, Next.js production build, and npm audit reporting 0 vulnerabilities.

Known risks:

- This is an auth foundation, not full SaaS auth. Organization/workspace roles,
  invites, password reset, MFA, and tenant isolation remain future checkpoints.
- Existing admin token compatibility is intentionally preserved for scripts,
  Render cron, Core sync, and recovery operations.
- Browser login now uses dashboard users; production deployments must configure
  `SECOPSAI_DASHBOARD_ADMIN_EMAIL` and `SECOPSAI_DASHBOARD_ADMIN_PASSWORD`.

## Checkpoint 007 - Approved Baseline Management

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Scope:

- Add durable, site-scoped baseline rules for known assets, accepted services,
  and trusted Wi-Fi BSSIDs.
- Apply baselines inside detection before findings are created or refreshed.
- Acknowledge existing matching findings and reopen them when the rule is
  disabled.
- Add clickable approval controls to Asset Detail and Wi-Fi, plus centralized
  management in Settings.
- Replace deprecated FastAPI startup events with the lifespan API.

Completed changes:

- Added Alembic revision `0004_baseline_rules` and the `baseline_rules` model.
- Added safe matcher validation, compatible finding-type validation, optional
  expiry, audit logs, reversible disable behavior, and deduplication.
- Asset approval covers `new_device` and `vendor_unknown` while preserving
  missing-device visibility.
- Service approval is scoped to asset, port, and protocol.
- Trusted BSSID approval suppresses `duplicate_ssid` but intentionally leaves
  `weak_wifi` active.
- Added baseline API CRUD and entity convenience endpoints.
- Added Asset, Wi-Fi, and Settings dashboard controls.
- Updated architecture, pilot, runbook, privacy, and README documentation.

Validation:

- Focused baseline and detection tests: 6 passed.
- `./scripts/edge test`: 42 backend/agent tests passed, 5 frontend test files
  with 8 tests passed, the Next.js static production build passed, and npm
  audit reported 0 vulnerabilities.
- Recursive AI evidence redaction is covered by regression tests.
- The FastAPI startup-event deprecation warning was removed; the remaining
  warning is from the upstream FastAPI/Starlette TestClient compatibility shim.
- SQLite migration replay reaches historical revision `0002`; revision `0003`
  uses PostgreSQL ALTER constraints, so the full Alembic chain must be replayed
  against PostgreSQL. Render remains the authoritative migration target.

Known risks:

- Baseline rules are single-deployment/site scoped; organization and tenant
  scoping belongs to the SaaS data-model checkpoint.
- The UI creates safe default rule types. Advanced custom rule selection is API
  only until policy administration is designed.

## Checkpoint 008 - Change Correlation, Audit, and Support Recovery

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Scope:

- Fix service-change correlation so multiple ports on one asset remain distinct.
- Add an authenticated operator audit-log API and dashboard screen.
- Add a redacted local support-bundle command and a clickable copy-command
  action in Settings.

Completed changes:

- Port-change correlation now includes IP, port, and protocol rather than
  collapsing all generic port-change titles for one asset.
- Added `GET /api/v1/audit-logs` with action, resource, sensor, and bounded
  result filtering.
- Added the Audit Log operator screen with search and resource filtering.
- Added `./scripts/edge support-bundle [--cloud] [--output ...]` with release,
  platform, dependency, API, worker, and recent-log diagnostics.
- Support bundles redact bearer tokens, common credential fields, and hardware
  identifiers, use owner-only file permissions, and never copy env-file
  contents.
- Added a `Copy Support Bundle` dashboard action and updated pilot/runbook/
  architecture/roadmap documentation.

Validation:

- Focused detection and audit API tests: 5 passed.
- `./scripts/edge test`: 44 backend/agent tests passed, 5 frontend test files
  with 8 tests passed, the Next.js static production build passed and includes
  `/audit`, and npm audit reported 0 vulnerabilities.
- `bash -n scripts/edge` passed.
- A real local support bundle was generated, checked for non-empty output,
  owner-only `0600` permissions, and absence of injected token values.

Known risks:

- Audit logs are deployment-scoped because organization/tenant ownership is not
  implemented yet.
- Support bundles intentionally preserve some local paths and authorized network
  ranges for troubleshooting; operators are warned to review before sharing.

## Checkpoint 009 - Operator UI Truth and Command Safety

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Scope:

- Validate the real dashboard at desktop and mobile viewports.
- Fix layout imbalance and non-functional command controls.
- Remove founder-specific local paths from the hosted dashboard defaults.

Completed changes:

- Rebalanced Overview into two independent operator columns, placing AI Insight
  below recent findings instead of stretching a mostly empty panel.
- Converted Local Commands into real keyboard-focusable copy buttons with
  success feedback.
- Replaced hard-coded `/Users/chrixchange/...` command paths with generic
  `$HOME/secopsai-edge` and `$HOME/secopsai` defaults.
- Added editable Edge/Core install-path fields that persist in browser local
  storage and immediately regenerate all commands.
- Added optional static-build path environment variables and ignored local
  Playwright artifacts.

Validation:

- `./scripts/edge test`: 44 backend/agent tests passed, 6 frontend test files
  with 10 tests passed, the Next.js static production build passed with all 15
  routes, and npm audit reported 0 vulnerabilities.
- Playwright screenshots were inspected at `1440x1000` and `390x844`.
- Final browser console check reported zero errors and zero warnings.
- Browser geometry confirmed Settings content remains within the 390px mobile
  viewport without overlap.

Known risks:

- Settings remains a long page on mobile. Splitting integrations and policy
  administration into dedicated routes is a later information-architecture
  improvement, not a pilot blocker.

## Checkpoint 010 - Dashboard Authentication Resilience

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Scope:

- Prevent unlimited password attempts against the public dashboard login.
- Enforce administrator roles at protected API boundaries.
- Improve dashboard API error messages without exposing credentials.

Completed changes:

- Added persistent `failed_login_count` and `locked_until` user fields with
  Alembic revision `0005_auth_lockout`.
- Added configurable attempt and lockout thresholds, defaulting to five attempts
  and fifteen minutes.
- Added generic invalid-login behavior, a dummy password verification path for
  unknown users, and audit events for failure, lockout, blocked login, and
  successful recovery.
- Added a 12-character minimum for the environment-bootstrapped admin password.
- Enforced `owner` or `admin` role in `require_admin`.
- Dashboard API errors now prefer safe FastAPI `detail` messages, including the
  temporary-lockout explanation.

Validation:

- Focused authentication and security tests: 10 passed.
- Tests cover lockout, correct-password blocking during lockout, expiry recovery,
  audit events, viewer rejection, and weak bootstrap-password rejection.
- `./scripts/edge test`: 47 backend/agent tests passed, 6 frontend test files
  with 10 tests passed, the static production build passed, and npm audit
  reported 0 vulnerabilities.

Known risks:

- Sessions are signed and expire, but session revocation, password reset, MFA,
  invitations, and organization membership remain SaaS-auth milestones.
- Unknown-email attempts use timing-resistant password verification but are not
  stored per address to avoid creating attacker-controlled account records.

## Checkpoint 011 - Core Product Story and Public Surface Alignment

Status: complete

Branches:

- Edge repo: `codex/pilot-hardening-foundation`
- Core repo: `codex/core-edge-hygiene`

Core commit:

- `ac13462 Make SecOpsAI Edge a first-class Core module`

Completed changes:

- Added SecOpsAI Edge to Core README positioning and platform support.
- Added Edge to the docs navigation, docs homepage, operator links, and Core
  ownership model.
- Removed founder-specific paths from Core Edge integration examples.
- Updated both maintained public-site sources so Edge asset/Wi-Fi discovery is
  visible in the hero, capabilities, terminal context, and platform matrix.
- Added the product-story change to the Core changelog.

Validation:

- Strict MkDocs build completed successfully to a temporary output directory.
- Focused Core integration and documentation tests: 9 passed.
- Full Core test suite: 221 passed.
- Public `www/` surface was inspected at `1440x1000` and `390x844` with
  Playwright; the browser console reported zero errors and zero warnings.

Known risks:

- The main operator console is still the Edge pilot dashboard. Public wording
  is unified, but canonical Core-backed web workflows remain a later product
  architecture milestone.

## Checkpoint 012 - OpenClaw Edge Context

Status: complete

Branch:

- OpenClaw plugin: `codex/plugin-release-hygiene`

Plugin commit:

- `9fab71c Expose Edge graph context to OpenClaw`

Completed changes:

- Added read-only OpenClaw tools for Edge assets, graph changes, and Edge-origin
  findings already synchronized into Core.
- Extended finding validation to accept canonical `EDGE-...` identifiers.
- Kept Edge/Core synchronization outside the plugin because write operations
  require an explicit approval design rather than an implicit tool call.
- Added executable contract tests for exact Core CLI arguments, database-path
  propagation, result rendering, and Edge identifier handling.

Validation:

- Plugin TypeScript build and two contract tests passed.
- npm audit reported 0 vulnerabilities.
- The real Core CLI returned valid JSON for graph assets, graph changes, and
  Edge-origin triage findings.

## Checkpoint 013 - Reliable Notification Delivery

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Completed changes:

- Replaced one-shot notification delivery with durable delivery records,
  immediate recorded attempts, bounded backoff, and terminal failure state.
- Added HMAC-SHA256 signatures, timestamps, event names, and delivery IDs to
  every webhook request.
- Added authenticated delivery-history, run-due, and manual-retry APIs without
  exposing retained payload bodies in API responses.
- Extended the existing Render scheduler to process both scan schedules and
  notification retries every five minutes.
- Added delivery history and one-click retry to Settings, with a degraded mode
  that preserves endpoint administration if history retrieval fails.
- Fixed the Settings mobile grid so long Core commands cannot widen the page,
  and added the missing branded browser icon.
- Documented server configuration and exact raw-body signature verification.

Validation:

- Notification tests cover signatures, site isolation, persisted retries,
  retry exhaustion, payload exclusion, history, and manual retry.
- `./scripts/edge test`: 51 backend/agent tests passed, 7 frontend test files
  with 11 tests passed, the static production build passed, and npm audit
  reported 0 vulnerabilities.
- Render scheduler and Edge shell script syntax checks passed.
- Playwright at `390x844` confirmed a 390px document width, contained Settings
  panels, and zero browser console errors or warnings.

Known risks:

- Delivery execution still occurs in API/cron processes. A dedicated queue
  worker becomes appropriate at higher tenant volume, but is not required for
  bounded pilot traffic.
- SMTP and Telegram credentials remain deployment-managed secrets and require
  provider-specific production configuration.
- Alembic reports `0006_notification_delivery` as the single head. The
  PostgreSQL migration was not replayed locally because Docker was unavailable;
  it must be verified by the normal Render migration step before pilot use.

## Checkpoint 014 - User and Session Lifecycle

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Completed changes:

- Added active state and session generations to dashboard users with Alembic
  revision `0007_user_lifecycle`.
- Server-side validation now rejects sessions after logout, password change or
  reset, role change, and account disablement.
- Added audited user list/create/update, password change, and logout APIs.
- Added a final-administrator guard so a deployment cannot remove its last
  active owner/admin account.
- Added dashboard user creation, role/state management, password reset, and
  signed-in password-change controls.
- Dashboard Disconnect now calls server logout before clearing browser state.

Validation:

- Auth tests cover logout revocation, password rotation, new-password login,
  user administration, and the final-administrator guard.
- Frontend tests cover user creation and access disablement.
- `./scripts/edge test`: 54 backend/agent tests passed, 8 frontend test files
  with 12 tests passed, the static production build passed, and npm audit
  reported 0 vulnerabilities.
- Alembic reports `0007_user_lifecycle` as the single migration head.

Known risks:

- Session generations revoke all of a user's sessions together. Per-device
  session inventory, MFA, and email-based recovery remain SaaS milestones.
- Viewer accounts exist in the canonical role model, but a dedicated read-only
  operator route policy is still required before they are useful in the UI.

## Checkpoint 015 - Sensor Runtime and Recovery

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Completed changes:

- Worker heartbeats now include agent version, OS, hostname, runtime state,
  active job ID, and bounded error context.
- Long-running scans maintain a background heartbeat so an active sensor does
  not appear offline while Nmap is still working.
- Added persistent sensor runtime state with Alembic revision
  `0008_sensor_runtime_state`.
- Repeated identical heartbeats refresh last-seen state without producing an
  unbounded audit row every 30 seconds; meaningful state transitions remain
  audited.
- Added sensor re-enable API/UI recovery and exposed version, OS, state, job,
  and last error in the Sites operator screen.

Validation:

- Agent tests cover idle and in-scan heartbeat metadata and shutdown.
- API tests cover runtime-state persistence, transition-only auditing, disable,
  and re-enable recovery.
- `./scripts/edge test`: 56 backend/agent tests passed, 8 frontend test files
  with 12 tests passed, the static production build passed, and npm audit
  reported 0 vulnerabilities.
- Alembic reports `0008_sensor_runtime_state` as the single migration head.

Known risks:

- Signed automatic sensor releases and fleet rollout rings are still later
  appliance/SaaS milestones. Pilot upgrades remain operator-managed.

## Checkpoint 016 - Supervised Edge-to-Core Sync

Status: complete

Branches:

- Edge repo: `codex/pilot-hardening-foundation`
- Core repo: `codex/core-edge-hygiene`

Completed changes:

- Added `./scripts/edge core sync-service` with install, start, stop, status,
  logs, run-now, and uninstall operations.
- macOS uses a launchd interval job; Linux uses a systemd user timer and
  one-shot service. Core sync and scanner worker lifecycles remain isolated.
- Added owner-only structured JSON configuration without credentials, safe
  environment-over-file precedence, and an advisory lock that skips
  overlapping timer/manual runs.
- Staged a standalone owner-executable sync runner outside macOS protected user
  folders, with credentials isolated in a separate `0600` JSON file and passed
  to Core only through the process environment.
- Added dashboard copy actions for installation, immediate sync, status, and
  logs, plus Core/Edge architecture, pilot, runbook, and support-bundle updates.
- Removed the final founder-specific Core path from Edge integration docs.

Validation:

- Cross-platform installer tests validate configuration permissions, launchd
  plist/systemd timer shape, interval bounds, real export/import arguments,
  authorization headers, lock cleanup, and overlap suppression.
- Shell syntax and frontend Core integration tests pass.
- `./scripts/edge test`: 59 backend/agent tests passed, 8 frontend test files
  with 12 tests passed, the static production build passed, and npm audit
  reported 0 vulnerabilities.
- Core full suite: 221 tests passed; strict MkDocs build passed.
- Real macOS launchd verification completed: 300-second timer running, no token
  in launch arguments, config/credentials `0600`, runner `0700`, and Core synced
  4 Edge assets plus 10 Edge findings.
- A real cloud-profile support bundle included sync health/log output and was
  verified not to contain the configured cloud administrator token.

Known risks:

- This milestone keeps Core local-first. A hosted Core ingestion API and
  unified Core-backed web console remain the next architecture milestone.
- Local service installation is per-user; appliance-wide Linux deployment will
  later use a system service/package instead of the pilot user timer.
- launchd cannot execute repositories stored in macOS privacy-protected
  Documents folders without Full Disk Access; the staged runner is the required
  service path and is covered by an installer regression test.

## Checkpoint 017 - Unified Core-Backed Edge Workspace

Status: complete

Branches:

- Edge repo: `codex/pilot-hardening-foundation`
- Core repo: `codex/core-edge-hygiene`
- Canonical dashboard: `codex/edge-unified-console`

Completed changes:

- Located the real SecOpsAI operator dashboard and added a dedicated Edge
  workspace without duplicating Core's findings or graph storage.
- Core CLI graph assets, graph changes, and `secopsai_edge` findings are the
  canonical read model; the Edge API optionally enriches it with sites,
  sensors, schedules, and active scan jobs.
- Edge administrator credentials remain server-side in the Python helper. The
  browser receives normalized operational data and an optional public sensor
  administration URL only.
- Added concurrent bounded Edge API reads, explicit Core/Edge health states,
  responsive tables, and desktop/mobile operator layouts.
- Removed the unused Tailwind development CDN dependency and hardened helper
  responses against normal client disconnects.

Validation:

- Dashboard Python suite: 31 tests passed.
- Dashboard Worker/UI suite and JavaScript syntax checks passed.
- Real helper verification loaded 4 Core graph assets, 10 Edge-origin
  findings, 1 live Edge sensor record, and scan-job context without returning
  an administrator token.
- Playwright desktop (`1440x1000`) and mobile (`390x844`) checks passed with
  no browser warnings or errors and no overlapping mobile header content.

Known risks:

- Hosted use still requires an intentionally deployed/authenticated Core
  helper because Core remains local-first; Cloudflare Pages cannot execute the
  Core CLI itself.
- Cross-surface write actions remain deliberately separate: canonical triage
  happens in Core, while scan/sensor administration remains in the Edge
  dashboard until a scoped command API is introduced.

## Checkpoint 018 - Independent Research Case Lifecycle

Status: complete

Branches:

- Core repo: `codex/core-edge-hygiene`
- Canonical dashboard: `codex/edge-unified-console`

Completed changes:

- Added Core-owned research cases, subjects, evidence, IOCs, linked findings,
  immutable events, disclosure state, and deterministic publication readiness
  to the local SQLite SOC store.
- Added complete `secopsai research case` CLI workflows for create, list, show,
  update, subject/evidence/IOC intake, finding links, notes, retraction, export,
  and readiness-gated review-draft creation.
- Added evidence-preserving retraction with required rationale; retracted data
  remains auditable but is excluded from readiness, reports, and publication.
- Added a general Original Research Blog Ops template. Drafts remain
  `needs_review`; explicitly structured hash IOCs survive redaction while
  unstructured secret-like values remain redacted.
- Added a canonical dashboard Research workspace with queue, readiness,
  disclosure, evidence, IOC, finding, timeline, Markdown download, and
  review-only blog handoff workflows.
- Added Worker/helper double authorization for every research mutation, a
  strict CLI argument allowlist, bounded report downloads, and no browser-side
  shell or embedded administrator credential.
- Added responsible-research and case-lifecycle documentation and repaired the
  published OpenClaw plugin reference for its existing Edge graph tools.

Validation:

- Core full suite: 228 tests passed; strict MkDocs build and docs/plugin
  contract verification passed.
- Dashboard: 34 Python tests, Worker/UI tests, JavaScript syntax checks, and
  diff checks passed.
- Isolated real browser verification passed on desktop and mobile with no
  warnings/errors: case creation, ready/blocked states, protected Markdown
  download, retraction modal, required reason, persisted retraction event, and
  publication blocker recalculation.

Known risks:

- Research storage is local-first and single-workspace. Organization/tenant
  ownership and remote researcher collaboration belong to the SaaS/MSP
  checkpoint.
- Dynamic malware execution is intentionally not built into the operator
  dashboard. It requires a separate disposable, network-controlled sandbox
  service and legal/ethical operating procedure.
- Blog drafts still require human editorial approval and deployment through
  Blog Ops; cases never auto-publish.

## Checkpoint 019 - Workspace Isolation and MSP Context

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Completed changes:

- Added organizations and user memberships with independent owner, admin, and
  viewer roles. Existing users and sites migrate into a stable Default
  Workspace without changing sensor, site, or telemetry identifiers.
- Added a signed active-workspace claim to dashboard sessions and server-side
  membership revalidation on every request. Role or membership changes revoke
  all prior sessions through the existing session generation.
- Scoped sites, sensors, jobs, schedules, assets, Wi-Fi, baselines, findings,
  reports, notifications, audit history, and Core bundles to the authenticated
  workspace. Sensor-token paths derive ownership from the sensor's site.
- Added owner-only workspace creation and switching APIs plus a responsive
  global workspace selector in the Edge console. Viewers now have useful
  read-only access; all mutations remain admin/owner protected.
- Changed user administration from global roles to workspace memberships,
  with per-workspace final-administrator protection and owner-only owner-role
  changes.
- Added Alembic revision `0009_organizations`, direct organization indexes for
  audit/notification records, and organization identity in Core bundle source
  metadata.

Validation:

- Full existing backend/agent suite passed after the tenancy change.
- Added adversarial two-workspace tests for list filters, guessed asset/finding
  IDs, cross-workspace writes, Core export isolation, workspace switching, and
  viewer write denial.
- Frontend: 9 test files with 13 tests passed; Next.js static production build
  and TypeScript validation passed.
- The complete Alembic chain upgraded to `0009_organizations`, downgraded to
  `0008_sensor_runtime_state`, and upgraded again against an isolated temporary
  PostgreSQL 14 cluster. The server, data directory, and temporary Homebrew
  compatibility links were removed after the drill.

Known risks:

- New non-default workspaces still need a one-time, workspace-scoped sensor
  enrollment flow; the legacy CLI registration token intentionally reaches
  only Default Workspace.
- Core's local graph records the workspace source identifier, but Core itself
  does not yet enforce hosted multi-tenant identity or provide a hosted ingest
  API.
- Billing, plan enforcement, and fleet release rings remain separate commercial
  milestones; they are not implied by workspace isolation.

## Checkpoint 020 - One-Time Sensor Enrollment

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Completed changes:

- Added workspace/site-scoped sensor enrollments with short expiry, HMAC-only
  secret storage, single-use consumption under a database row lock, explicit
  revocation, immutable used/revoked timestamps, and audit events.
- Added authenticated create/list/revoke enrollment APIs and a public token
  exchange endpoint that returns only the new sensor credential. List APIs
  never return the enrollment secret.
- Added Alembic revision `0010_sensor_enrollments` with organization/site/user
  ownership and lookup indexes.
- Added `./scripts/edge cloud enroll <token>` and
  `./scripts/edge onboard --cloud --enrollment-token <token>`. Cloud installers
  now accept the one-time token and do not persist it or require a customer to
  receive the platform administrator token.
- Added a real `Enroll sensor` action to each site, pending-enrollment state,
  revoke control, one-time secret panel, and copyable exact installer command.
- Replaced hand-built registration JSON in the shell helper with structured
  Python JSON encoding so host/site/sensor names cannot break request syntax.

Validation:

- API tests cover one-time use, HMAC storage, replay denial, foreign-site
  denial, revocation, expiry state, and sensor-to-site ownership.
- A frontend interaction test clicks `Enroll sensor` and verifies the
  generated installer action; shell syntax, frontend suite, TypeScript, and the
  static Next.js build pass.
- The full Alembic chain upgraded to `0010_sensor_enrollments`, downgraded to
  `0009_organizations`, and upgraded again against an isolated PostgreSQL 14
  cluster with complete cleanup.

Known risks:

- Distribution still assumes the sensor package/repository is already present
  on the target. A signed downloadable release artifact and update channel are
  required before broad self-service deployment.
- Enrollment is deliberately an installation credential, not a general API
  token; it cannot be refreshed or used for dashboard access.

## Checkpoint 021 - Operational Release Gates

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Completed changes:

- Split liveness and readiness: `/healthz` returns process/build identity;
  `/readyz` verifies PostgreSQL and exact Alembic head. Added an authenticated
  safe system-status endpoint and clickable Settings health panel with Refresh.
- Added deployment environment, release version/commit, schema head, database
  pool timeout/recycle, and fail-closed production configuration validation.
- Reconciled pre-existing ORM/migration index drift and added revision
  `0011_schema_alignment`; `alembic check` now reports no upgrade operations.
- Added locked Python dependencies, Python/Node vulnerability audit gates, a
  PostgreSQL 16 GitHub Actions service, migration upgrade/downgrade, full test
  suites, static build, tracked-output checks, and backup/restore CI drill.
- Added `./scripts/edge release-check` for a repeatable local release gate and
  switched Render/local setup to the locked dependency set.
- Added guarded PostgreSQL custom-archive create/verify/restore commands,
  owner-only output, required-table verification, exact target-name
  confirmation, remote-target opt-in, RPO/RTO targets, and rollback runbook.
- Changed Render health routing to `/readyz` while retaining `/healthz` for
  process diagnostics. The Blueprint remains explicitly `pilot` and free-tier
  so paid infrastructure is never created silently.
- Aligned API, agent, dashboard, and Edge bundle versions at `0.2.0`.

Validation:

- Python dependency audit reported no known vulnerabilities; npm audit remains
  clean at the configured moderate threshold.
- API tests cover liveness identity, exact-schema readiness, authenticated safe
  system status, and production configuration rejection/acceptance.
- The health panel interaction test covers load and Refresh; full TypeScript
  and static Next.js build pass.
- Against an isolated PostgreSQL 14 cluster, the complete migration chain
  reached `0011_schema_alignment`, `alembic check` found no drift, downgrade and
  re-upgrade passed, and a custom backup restored into a second database with
  the expected schema revision. All temporary state was removed.

Known risks:

- The checked-in Render Blueprint remains free-tier demo infrastructure. A paid
  pilot must move API/PostgreSQL to paid plans with provider-managed backups and
  an external uptime check.
- CI is defined locally but will not protect the default branch until this
  branch is pushed and repository branch protection requires the workflow.
- The lock file is exact but not hash-locked; adding a controlled dependency
  update bot and hash-generating lock workflow is a later supply-chain hardening
  improvement.

## Checkpoint 022 - Verified Sensor Distribution and Upgrade

Status: complete

Branch:

- Edge repo: `codex/pilot-hardening-foundation`

Completed changes:

- Added a committed-content release builder that requires API, agent, and web
  versions to match and emits a versioned sensor archive plus SHA-256 manifest.
- Added a standalone HTTPS bootstrap for first install and explicit upgrades.
  It validates the exact checksum filename and digest, rejects traversal,
  links, devices, FIFOs, and multi-root archives, then extracts into a private
  temporary directory.
- Preserved local sensor credential files across upgrades, retained the prior
  installation for recovery, and added automatic rollback when the new
  installer fails.
- Changed appliance installation to skip dashboard dependencies while keeping
  the developer setup unchanged. Hardened empty-array handling for the Bash
  version shipped with older macOS releases.
- Added a tag-only GitHub release workflow with full release-gate verification,
  a default-branch ancestry check, versioned and `latest` assets, checksums,
  and GitHub build-provenance attestations.
- Changed the Sites enrollment action into a one-time, copyable bootstrap
  command so a pilot user no longer clones or understands the repository.

Validation:

- Shell syntax checks passed for the helper, installer, bootstrap, builder,
  and release gate.
- Distribution tests passed for first install, argument forwarding,
  credential-preserving upgrade, failed-upgrade rollback, and rejection of an
  archive traversal entry.
- Focused worker and Sites enrollment tests passed; the Next.js production
  build and TypeScript validation passed.
- The full release gate is rerun against the committed checkpoint before a tag
  can be published, and the tag workflow repeats that gate on the exact release
  commit.

Known risks:

- No downloadable `v0.2.0` asset exists until this branch is merged and the
  verified tag workflow succeeds; the dashboard intentionally targets the
  latest release endpoint that will become valid at that point.
- This is a manual upgrade channel with rollback, not unattended fleet rollout
  rings. Staged auto-update policy belongs after a paid pilot proves the sensor
  recovery workflow.
- GitHub and HTTPS are part of the sensor software-delivery trust boundary.
  Checksums detect corruption or asset mismatch; build attestations provide
  provenance for operators that enforce verification.

## Checkpoint 023 - Workspace-Scoped Core Synchronization

Status: complete

Branches:

- Edge repo: `codex/pilot-hardening-foundation`
- Core repo: `codex/core-edge-hygiene`

Completed changes:

- Replaced the automatic Core sync dependency on a platform administrator
  secret with expiring, revocable integration credentials limited to the
  `core:export` scope and the active workspace.
- Added HMAC-only integration-token storage, one-time plaintext display,
  expiry, revocation, last-use tracking, audit events, and Alembic revision
  `0012_integration_tokens`.
- Added Settings controls to create, copy once, inspect, and revoke Core export
  credentials. Viewers receive a read-only explanation and cannot enumerate or
  create tokens.
- Restricted integration tokens to the normalized Core bundle endpoint. They
  are explicitly rejected by asset, scan, sensor, user, and general dashboard
  authorization paths.
- Updated Core CLI and the supervised sync runner to prefer
  `SECOPSAI_EDGE_ACCESS_TOKEN`/`--access-token`. Existing admin-token names and
  owner-only credential files remain readable only for migration compatibility.
- Updated copied commands to request the credential with cross-shell Python
  `getpass`, keeping plaintext out of shell history and service arguments.
- Removed a stale founder-specific path and legacy admin-token installer from
  dashboard Onboarding; the primary action now opens Sites for one-time sensor
  enrollment.

Validation:

- Edge full suite: 74 backend/agent tests and 17 frontend tests passed;
  TypeScript, static Next.js production build, shell/Python syntax checks, and
  npm audit passed with zero vulnerabilities.
- Core full suite: 229 tests passed, including scoped access-token environment
  precedence and legacy compatibility.
- Adversarial API tests cover one-time secret visibility, HMAC storage,
  cross-workspace export isolation, denial on unrelated endpoints, expiry,
  revocation, foreign revocation denial, bad scope rejection, and viewer denial.
- Against an isolated UTF-8 PostgreSQL 14 cluster, migrations upgraded to
  `0012_integration_tokens`, `alembic check` found no drift, downgrade reached
  `0011_schema_alignment`, and re-upgrade restored the integration-token table.
  The server, data directory, and temporary Homebrew compatibility links were
  removed afterward.

Known risks:

- Tokens currently expire after 90 days from the dashboard and require manual
  replacement in the supervised sync service. Rotation reminders and
  overlap/grace-period rotation belong to fleet operations.
- The canonical dashboard's optional live Edge enrichment still uses a
  server-side administrator credential for broader sensor/site/job reads. A
  separate scoped operations API credential should replace it before hosted
  multi-tenant dashboard deployment.
- The legacy platform admin token remains available for the scheduler and
  emergency recovery. New Core sync installations no longer need it.

## Checkpoint 024 - Node 24 CI and Release Actions

Status: complete

Branch:

- Edge repo: `codex/ci-node24-actions`

Completed changes:

- Replaced GitHub Actions that still targeted the deprecated Node 20 runtime
  with the official Node 24 releases of checkout, setup-python, and setup-node.
- Upgraded build-provenance attestation from v2 to v4 before publishing the
  first sensor release.
- Pinned every changed action to its resolved full commit SHA with the major
  release retained as an audit comment, avoiding mutable-tag execution in the
  privileged release workflow.

Validation:

- Both push and pull-request instances of the full Edge CI workflow passed.
- Each workflow repeated PostgreSQL migration/drift/rollback, backend/agent
  tests, dependency audit, sensor archive inspection, backup/restore, frontend
  tests/build/audit, and clean-state verification.
- GitHub reported zero annotations for both jobs; the prior Node 20 deprecation
  warning is removed.

Known risks:

- Action SHA updates are intentionally manual until a dependency-update bot is
  configured with review and CI gates.
- Node 24 actions require current GitHub-hosted or self-hosted runner versions;
  this project currently uses GitHub-hosted Ubuntu runners.

## Checkpoint 025 - Private Repository Release Recovery

Status: complete

Branch:

- Edge repo: `codex/private-release-attestation`

Incident and decision:

- The first `v0.2.0` tag passed its exact-commit release gate and built the
  archive, but GitHub rejected provenance persistence because artifact
  attestations are unavailable for user-owned private repositories.
- Publication stopped before `gh release create`, so `v0.2.0` has no release
  page or downloadable assets. The published annotated tag was not deleted,
  moved, or rewritten.
- The patch release advances to `0.2.1` with the repository remaining private;
  making product source public is a founder decision, not an automated release
  workaround.

Completed changes:

- Made provenance attestation mandatory when the repository is public and
  replaced it with an explicit workflow notice plus SHA-256 manifests when the
  GitHub feature is unavailable to a private repository.
- Kept the release gate, default-branch ancestry requirement, committed-content
  archive, HTTPS bootstrap, exact checksum verification, and protected upgrade
  rollback unchanged.
- Removed the hard-coded package version from CI; archive validation now derives
  the shared API/agent/dashboard version.
- Advanced API, agent, dashboard, docs, and regression fixtures to `0.2.1`.

Validation:

- Both push and pull-request instances of the full Edge CI workflow passed for
  the private-release patch.
- Workflow YAML, shell syntax, focused worker/distribution tests, frontend test,
  TypeScript, and static production build passed locally.
- The release workflow's private/public condition is exercised by the actual
  private `v0.2.1` tag only after this checkpoint reaches verified `main`.

Known risks:

- A private release has checksum integrity and a GitHub-authenticated delivery
  channel, but not a persisted Sigstore/GitHub provenance attestation. Operators
  requiring signed provenance should use a public repository or a separately
  managed organizational signing service.
- `v0.2.0` remains an unreleased historical tag documenting the failed provider
  capability check. The first downloadable pilot package is intended to be
  `v0.2.1`.

## Checkpoint 026 - Private Pilot Release Installation

Status: complete

Branch and release:

- Edge implementation PR: `#4` (`codex/private-release-downloads`)
- Merge commit: `f315e12aa5a0ad0711acba1e925ec80c3215c30e`
- Published release: `v0.2.2`

Incident and decision:

- The `v0.2.1` release was valid and downloadable by authenticated GitHub
  users, but the dashboard copied an unauthenticated `curl` command. That
  command returns `404` while the pilot repository is private.
- The repository remains private. Private pilot operators must have explicit
  collaborator access and authenticate GitHub CLI with `gh auth login`; the
  GitHub credential remains outside the copied one-time sensor command.
- Public HTTPS downloads remain supported automatically if the repository is
  made public through a separate founder decision.

Completed changes:

- Added `auto`, `gh`, and `curl` release download modes to the sensor bootstrap.
  Auto mode prefers an authenticated GitHub CLI and otherwise uses the
  HTTPS-only public release path.
- Updated the Sites enrollment action to copy a command that handles private
  GitHub access, reports missing repository permission clearly, and carries
  only the short-lived sensor enrollment token.
- Added deterministic tests for authenticated private downloads, public
  downloads, checksum verification, safe archive extraction, credential-
  preserving upgrades, and rollback.
- Made release version checks read API, agent, and dashboard versions from
  committed `HEAD`; the release gate now refuses dirty staged or unstaged
  content. This prevents an archive from being named with a working-tree
  version while containing the previous commit.
- Advanced API, agent, dashboard, docs, and regression fixtures to `0.2.2`.

Validation:

- Local product suite passed with 76 backend/agent tests, 17 frontend tests,
  static Next.js production export, and zero npm audit vulnerabilities.
- The clean-commit release gate verified
  `secopsai-edge-0.2.2.tar.gz` at implementation commit `ad7d760`.
- Both pull-request and push CI checks passed; main CI passed at merge commit
  `f315e12` with PostgreSQL migration rollback/re-upgrade, schema drift,
  backup/restore, release archive, backend, frontend, and dependency checks.
- The tag workflow published five assets. Both versioned and latest checksum
  manifests passed, the two archives were byte-identical, and the published
  bootstrap was byte-identical to `v0.2.2:scripts/bootstrap-secopsai-edge.sh`.
- Extracted release contents reported `0.2.2` consistently for API, agent, and
  dashboard.

Known risks:

- Private pilot installation requires GitHub collaborator administration and
  GitHub CLI authentication. A customer-ready commercial distribution channel
  should use a private artifact service, signed package repository, or public
  release policy that does not require source-repository membership.
- User-owned private repositories still cannot persist GitHub artifact
  attestations. SHA-256 manifests are generated by the verified tag workflow;
  organization-managed signing remains a later supply-chain hardening task.

## Checkpoint 027 - Scoped Dashboard Operations Access

Status: complete

Branches, merges, and release:

- Edge implementation PR: `#6` (`codex/operations-read-token`)
- Edge merge commit: `8077b9836f664efaa57bcfb099ca7ac6850f279b`
- Dashboard implementation PR: `#5` (`codex/edge-operations-token`)
- Dashboard merge commit: `920fcfa611ae9b9237ec575a22a5ad3faa875188`
- Published Edge release: `v0.2.3`

Completed changes:

- Added an expiring, revocable `operations:read` integration scope for the
  canonical dashboard's server-side Edge enrichment. It can read only sites,
  sensors, scan schedules, and scan jobs in its assigned workspace.
- Kept `core:export` and `operations:read` separate. Operations credentials
  cannot export the Core bundle, read asset/finding telemetry, or call any
  mutating endpoint.
- Removed stale-job recovery and database commits from the sensor-listing GET
  endpoint. Recovery remains in the authenticated sensor job-claim path.
- Changed newly created integration secret prefixes to the neutral
  `secopsai_integration_` form while preserving recognition of deployed
  `secopsai_core_` credentials for migration compatibility.
- Added separate dashboard controls to create Core export and dashboard
  operations credentials, with scope and expiry visible before copying the
  one-time secret.
- Updated the canonical dashboard helper to prefer
  `SECOPSAI_EDGE_OPERATIONS_TOKEN`. The legacy platform-admin environment
  variable remains a deprecated fallback and produces an operator warning.
- Rotated the live dashboard helper to a dedicated 90-day operations token,
  stored only in its ignored owner-readable `.env`; no platform admin token is
  present in that helper configuration.
- Advanced the Edge API, agent, dashboard, bootstrap, documentation, and test
  fixtures to `0.2.3`.

Validation:

- Edge full suite passed with 78 backend/agent tests and 18 frontend tests;
  TypeScript, static Next.js production export, shell/Python checks, and npm
  audit passed with zero vulnerabilities.
- Canonical dashboard validation passed with 36 Python tests, Worker contract
  tests, and JavaScript syntax checks.
- Live authorization probes confirmed the operations credential can read the
  four intended collections and receives `403` for Core export, assets, and a
  site mutation.
- Render reports API version `0.2.3` at Edge merge commit `8077b9836f66`.
- Cloudflare production deployment `7764987e-47e6-4497-8ca3-812344da12d4`
  serves canonical dashboard source commit `920fcfa`.
- The `v0.2.3` release workflow completed successfully at the exact Edge merge
  commit. Both checksum manifests passed, the latest and versioned archives
  were byte-identical, the published bootstrap matched the extracted archive,
  and API, agent, and dashboard versions were all `0.2.3`.
- Edge, Core, canonical dashboard, and OpenClaw plugin worktrees were clean and
  synchronized with their remote default branches after the merges.

Known risks:

- The live dashboard operations credential expires after 90 days. Rotation
  reminders, overlap-based replacement, and expiry visibility in the operator
  console remain fleet-operations work.
- The canonical dashboard helper is configured locally. A separately hosted
  helper deployment must receive the operations credential in server-side
  secret storage; it must never be exposed as a Pages browser variable.
- The deprecated administrator-token fallback remains for migration only and
  should be removed in a future breaking release after all helper deployments
  are confirmed on scoped credentials.
- Core autoresearch PRs `#23` through `#25` predate this work and remain open.
  They are intentionally excluded from product merges pending an independent
  evaluation of their threshold changes.

## Checkpoint 028 - Integration Credential Rotation

Status: complete

Branches, merges, and release:

- Edge implementation PR: `#8` (`codex/integration-token-rotation`)
- Edge merge commit: `76d8184e80714e8ec6903f3b74dff72cf7d3cc85`
- Canonical dashboard implementation PR: `#6` (`codex/edge-token-expiry`)
- Canonical dashboard merge commit: `a2aeaf26c8848e3eab54e308ef62df28ad6597dd`
- Published Edge release: `v0.2.4`

Completed changes:

- Added scoped credential self-inspection that returns only identifier, scope,
  state, expiry, last-use, and creation metadata. Plaintext secrets are never
  persisted or returned after creation.
- Added a 14-day rotation recommendation to the API, Edge Settings, and the
  canonical dashboard's live Edge health view.
- Added audited one-click rotation that creates a second credential with the
  same workspace and scopes. The previous credential remains active until the
  operator updates and verifies the consumer, then revokes it.
- Added visible short IDs and creation timestamps so overlapping old and new
  credentials cannot be confused. Every rotate/revoke action has a unique
  accessible name.
- Made canonical dashboard self-status enrichment tolerant of rolling upgrades:
  unavailable lifecycle metadata produces a warning without hiding otherwise
  healthy live sites, sensors, schedules, or jobs.
- Replaced stale canonical-dashboard documentation that still presented the
  platform administrator token as the primary Edge helper credential.
- Advanced API, agent, dashboard, bootstrap, deployment examples, and release
  tests to `0.2.4`.

Validation:

- Edge full suite passed with 81 backend/agent tests and 19 frontend tests;
  TypeScript, static Next.js production export, Python/shell checks, and npm
  audit passed with zero vulnerabilities.
- The clean-commit release gate rebuilt and inspected the sensor archive at
  implementation commit `af10478`.
- Canonical dashboard validation passed with 38 Python helper tests, Worker
  contract tests, and JavaScript syntax checks.
- API tests cover self-only metadata, administrator-token denial on self-status,
  foreign/revoked rotation denial, both-token overlap, HMAC-only replacement
  storage, and rotation audit evidence.
- Both PR gates and Edge main CI passed. Release workflow `29228489146`
  published `v0.2.4` from the exact merge commit.
- Both release checksum manifests passed, latest/versioned archives were
  byte-identical, the standalone bootstrap matched the archive, and API, agent,
  and dashboard versions all reported `0.2.4`.
- Render served API version `0.2.4` at commit `76d8184e8071`; readiness reported
  schema `0012_integration_tokens`.
- Live self-inspection of the configured `operations:read` credential returned
  active state, 90 days remaining, and no secret. The canonical helper then
  loaded one site, one sensor, four scan jobs, and matching lifecycle status.
- Cloudflare production deployments serve Edge source `76d8184` as deployment
  `759e0eb3-f9ab-4f3b-8570-763b34600778` and canonical dashboard source
  `a2aeaf2` as deployment `799a6d57-d988-40b5-b522-136f85048c60`.

Known risks:

- Rotation is operator-confirmed by design. Automatic revocation could cause an
  outage when a helper or Core service has not actually reloaded its secret.
- The canonical dashboard helper's live token is owner-readable local config.
  A hosted helper must use its platform's server-side secret manager and repeat
  the verify-before-revoke workflow.
- The in-app visual browser could not attach after two retries during deployed
  QA. Rendered component interactions, TypeScript/static production build,
  deployed-source identity, and live helper/API checks passed; desktop/mobile
  visual regression verification remains queued for the next available browser
  session.

## Checkpoint 029 - Client-Ready PDF Reports

Status: complete

Branches, merge, and release:

- Edge implementation PR: `#10` (`codex/pdf-report-export`)
- Edge merge commit: `ee5b21d7d3684f7627ffad0b996f28be69a375e7`
- Published Edge release: `v0.2.5`
- Release workflow: `29230621669`

Completed changes:

- Added authenticated, workspace-scoped A4 PDF export at
  `GET /api/v1/reports/{report_id}/export.pdf` while retaining HTML and browser
  print fallbacks.
- Added a frozen seven-day reporting period and operational metrics covering
  assets, new devices, risky services, Wi-Fi risks, finding state, completed
  scans, and open severity.
- Added a professional multi-page report layout with site/build metadata,
  executive metrics, severity summary, ordered remediation actions, normalized
  findings, technical notes, page numbers, and an explicit privacy boundary.
- Embedded Unicode-capable fonts, escaped report content, excluded evidence
  objects, and normalized attachment filenames to ASCII-safe slugs.
- Added the dashboard PDF action, visible report period/metrics, user feedback,
  and interaction tests for PDF and HTML downloads.
- Updated the README, pilot guide, demo script, runbook, installer/deployment
  examples, Core contract example, and roadmap to match the current product.
- Advanced API, agent, dashboard, bootstrap, deployment examples, and release
  tests to `0.2.5`.

Validation:

- The clean-commit release gate passed with 84 backend/agent tests, 21 frontend
  tests, TypeScript, static Next.js export, Python/shell checks, PostgreSQL
  migration/restore coverage, Python dependency audit, zero npm vulnerabilities,
  and a verified `0.2.5` sensor archive.
- A stress fixture with Unicode site text and 12 findings rendered to three A4
  pages. Every page was inspected as a PNG; headings/findings stayed together,
  text did not clip or overlap, page numbers were present, and the final privacy
  boundary rendered correctly.
- PR checks and post-merge `main` workflow `29230483463` passed before the tag
  was created.
- Release checksums passed, latest/versioned archives were byte-identical, the
  standalone bootstrap matched the archive, and API/agent/web versions all
  reported `0.2.5`.
- Cloudflare production deployment `bd86fc83-0541-4649-a950-cbdad6d69374`
  serves Edge source `ee5b21d`.
- The first Render rollout failed safely while `0.2.4` remained live because
  the service configuration had drifted from `render.yaml` and still installed
  the old split requirements. The API and scheduler were reconciled to
  `pip install -r requirements.lock`, API health routing was reconciled to
  `/readyz`, and auto-deploy remained enabled.
- Corrected Render deployment `dep-d9a90o77f7vs739cbr10` is live on exact
  commit `ee5b21d`; `/healthz` reports `0.2.5` and `/readyz` reports schema
  `0012_integration_tokens`.
- A hosted report was generated and downloaded through the production PDF
  endpoint. It returned HTTP 200, `application/pdf`, an attachment header, and
  a parseable two-page 78,082-byte document containing the report title and
  privacy boundary.

Known risks:

- The current Render Postgres resource is a free database and reports expiry on
  2026-07-20. It must be upgraded or replaced after a verified export before
  relying on it for pilot data; no paid plan was selected without founder
  authorization.
- The PDF is visually validated but is not yet a tagged PDF/UA accessibility
  artifact. Keep HTML as the accessible fallback until tagged output is added.
- The current machine could not resolve `pages.dev` during the final HTTP fetch,
  and the independent web fetch rejected the preview URL. Wrangler confirmed
  the production deployment and exact source, but an external desktop/mobile
  browser smoke pass remains required when DNS/browser access is available.
- The live Render service can drift from the checked-in Blueprint. A future
  operations checkpoint should automate drift detection for build command,
  health path, branch, and auto-deploy state.

## Checkpoint 030 - Hosted Data Recovery And Render Drift Guard

Status: complete

Branch and release target:

- Edge implementation PR: `#12` (`codex/render-operations-checkpoint-030`)
- Edge merge commit: `2a1119363a03eb9212af1ef0760a3fc0e20cd235`
- Published release: `v0.2.6`
- Release workflow: `29234298216`

Completed changes:

- Added `./scripts/edge cloud drift-check`, which validates `render.yaml` with
  Render and compares the live API, five-minute scheduler, and PostgreSQL
  resource against the expected repository, branch, build/start commands,
  health path, schedule, availability, and PostgreSQL major version.
- Added safe human and JSON output, deterministic timestamps for tests,
  free-database expiry warnings, and an optional `--fail-on-warning` operations
  gate. The checker does not read or print service environment variables.
- Added `./scripts/edge cloud backup`, which uses the authenticated Render CLI,
  temporarily allowlists the current public IP, preserves/restores the original
  allowlist, selects Render's exact PostgreSQL client major through Docker,
  verifies required archive tables, and creates an owner-only SHA-256 manifest.
- Hardened local backup/restore so a host PostgreSQL client-major mismatch uses
  the matching official PostgreSQL Docker image. Localhost targets are safely
  translated to the Docker host gateway.
- Added copyable Render drift-check and hosted-backup commands to Settings and
  documented the recovery boundary in the README, runbook, deployment guide,
  security boundaries, and roadmap.
- Advanced API, agent, dashboard, installer examples, and release tests to
  `0.2.6` because the operational tools ship in the sensor archive.

Validation to date:

- Unit tests cover a matching Render inventory, build/health drift, free-plan
  expiry, warning gates, connection-secret non-disclosure, archive writes, and
  Render CLI version probing.
- The live Render Blueprint passed validation. The API, scheduler, and
  PostgreSQL resources match the deployment contract; the checker reports the
  expected warning that the free database expires on 2026-07-20.
- The first recovery drill deliberately caught an invalid combination: a
  PostgreSQL 18 host archive could not restore into PostgreSQL 16 because of
  the newer `transaction_timeout` setting. The new matching-client fallback
  then created and restored a local PostgreSQL 16 archive successfully.
- The hosted backup workflow replaced the incompatible emergency archive with
  a PostgreSQL 16 archive, restored Render's original empty IP allowlist, and
  passed its checksum. An isolated PostgreSQL 16 restore recovered schema
  `0012_integration_tokens`, 4 assets, 10 findings, 3 reports, and 4 scan jobs.

Known risks and next actions:

- Render PostgreSQL remains on the free plan and expires on 2026-07-20. The
  archive now protects the demo data, but provider-managed backups and
  point-in-time recovery still require an explicitly authorized paid plan.
- Render deployment `dep-d9a9o4c2m8qs73deveig` serves exact merge
  `2a11193`; `/healthz` reports `0.2.6` and `/readyz` reports schema
  `0012_integration_tokens`.
- Post-merge `main` workflow `29234147799` passed migrations, 92
  backend/agent tests, Python/Node audits, package inspection, PostgreSQL 16
  backup/restore, 21 frontend tests, static build, and generated-state checks.
- Release checksums passed, latest/versioned archives were byte-identical, the
  standalone bootstrap matched the archive, and API/agent/web versions all
  reported `0.2.6`.
- Cloudflare production deployment `a27b25b5` serves exact merge `2a11193`
  with the hosted API URL and demo mode disabled.

## Checkpoint 031 - Clipboard Resilience And Deployed Browser QA

Status: complete

Branch and release target:

- Edge implementation PR: `#13` (`codex/copy-command-resilience`)
- Edge merge commit: `b14e89229cb5ef3c254941d9dfadc129353dd609`
- Published release: `v0.2.7`
- Release workflow: `29236074750`

Completed changes:

- Ran the deployed Edge console through the in-app browser on desktop and at
  `390x844`. Overview and Settings rendered meaningful content with no console
  warnings/errors, no framework overlay, and no mobile horizontal overflow.
- Confirmed the new Render drift-check and hosted-backup controls are visible
  in Settings. The browser interaction exposed a real permission edge case:
  Clipboard API rejection left the copy button in its idle state without
  telling the operator that copying failed.
- Added a synchronous copy fallback for browsers that expose but deny the
  asynchronous Clipboard API, an accessible success/failure state, cleanup of
  temporary DOM state and timers, and focused tests for success, fallback, and
  terminal failure.
- Advanced the package to `0.2.7` so the deployed UI and private sensor archive
  retain one traceable version identity.

Validation:

- Post-merge `main` workflow `29235924658` passed migrations, 92 backend/agent
  tests, Python/Node audits, package inspection, PostgreSQL backup/restore, 24
  frontend tests, the static production build, and generated-state checks.
- Release checksums passed, latest/versioned archives were byte-identical, the
  standalone bootstrap matched the archive, and API/agent/web versions all
  reported `0.2.7`.
- Render deployment `dep-d9aa67mk1jcs73freob0` serves exact merge `b14e892`;
  `/healthz` reports `0.2.7` and the matching commit.
- Cloudflare production deployment `28587756-ecdf-4c05-95ea-922fbf8a4d27`
  serves exact merge `b14e892` with demo mode disabled.
- A local browser permission-denial test confirmed the same copy action moved
  to its accessible `Copied` state through the synchronous fallback. The
  deployed Settings page was then rechecked at `1440x1000` and `390x844`: the
  operations commands were present, the console was clean, and the mobile page
  had no horizontal overflow (`clientWidth == scrollWidth == 390`).

Known limitations:

- Browser clipboard behavior is permission-dependent. The UI now reports
  success or failure explicitly and keeps the command visible for manual
  selection when both browser copy mechanisms are unavailable.

## Checkpoint 032 - Mission Control Authentication And RLS Staging

Status: complete (activation staged)

Dashboard branch, PR, and deployment:

- Dashboard implementation PR: `#7` (`codex/dashboard-auth-rls-hardening`)
- Dashboard merge commit: `77e4eefd54e7af90f9c361b5436b731a65dcac23`
- Cloudflare production deployment:
  `a6df9b7c-b963-42c1-96f4-5f2247bdd5de`

Completed changes:

- Added invitation-only Supabase Auth gating to the canonical SecOpsAI Mission
  Control dashboard, including session restoration, sign-in, sign-out,
  reset-link request, and recovered-password update flows.
- Added an authenticated single-tenant pilot migration covering every
  browser-backed table. It removes anonymous table/view access, rejects
  anonymous-auth users, protects findings views, and removes public execution
  from dashboard RPC functions.
- Added `scripts/dashboard-security apply|verify` so RLS rollout is repeatable
  and fails unless every present dashboard table has RLS, all four authenticated
  CRUD policies, and zero anonymous policies, grants, or function access.
- Replaced the unversioned Supabase browser dependency with exact
  `@supabase/supabase-js@2.110.2` plus SHA-384 Subresource Integrity.
- Added Worker-enforced CSP, anti-framing, content-type, referrer, permissions,
  opener, and transport-security headers to static and API responses.
- Removed inline JavaScript and inline script event handlers so the script CSP
  does not require `unsafe-inline`.

Validation:

- Dashboard Node checks and Worker tests passed; 41 Python tests passed.
- A PostgreSQL 16 migration drill applied both historical schemas and the new
  policy through the shipped command. Verification reported 6/6 tables with
  RLS, 24 authenticated policies, and zero anonymous policies, grants, or
  function privileges.
- Local and Cloudflare preview browser QA passed on desktop and `390x844`:
  the auth gate rendered meaningful content, reset validation responded, the
  protected app shell remained hidden, the console was clean, and mobile had no
  horizontal overflow.
- The production deployment serves exact merge `77e4eef`; the encrypted
  `DASHBOARD_AUTH_REQUIRED=false` rollout guard kept the existing dashboard
  available instead of locking out the operator before database activation.

Activation required:

- A live anonymous REST read still returned HTTP 200 with one finding before
  this migration was applied. No Supabase access token or direct database
  credential is configured on this machine, so changing the live database was
  not possible without inventing or exposing credentials.
- Before enabling authentication, provide an authorized direct database URL,
  run `scripts/dashboard-security apply`, create or confirm an invited operator,
  set the Cloudflare `DASHBOARD_AUTH_REQUIRED` secret to `true`, and prove the
  anonymous REST request is denied. Until then, production remains a demo-only
  surface and must not hold real customer data.

## Checkpoint 033 - Protected Hosted Core Ingestion

Status: complete

Branches and merged dependencies:

- Core PR: `#38` (`codex/core-ingestion-api`)
- Core merge: `6ceb4310c16f8cef068abac4b13351c8ba191174`
- Edge PR: `#16` (`codex/hosted-core-push`)
- Edge merge: `f554a786b96ada97a4a48ad2aebaf1c284742871`
- Edge release: `v0.2.8`

Completed changes:

- Added the organization-scoped Core FastAPI ingestion/read boundary with
  separate ingest/read credentials, minimized workspace responses, import
  audit history, strict CORS/trusted hosts, bounded bundle contracts, and raw
  scanner telemetry rejection.
- Changed Edge source identity from version-scoped to organization-scoped so a
  routine Edge upgrade does not create a second Core sync cursor.
- Added `./scripts/core-api configure-local|run|check|status` and a Render
  Blueprint validated by Render CLI for one Starter instance plus a 1 GB
  persistent disk. No paid service was created automatically.
- Added `./scripts/edge core push --cloud --core-api-url ...` and hosted mode
  for the supervised `core sync-service`. Hosted transfer needs no Core repo on
  the sensor host and keeps both scoped credentials out of process arguments.
- Hardened the staged bridge with owner-only credentials/output, no redirects,
  HTTPS for non-loopback endpoints, bounded responses, overlap locking, and
  explicit Core import confirmation.
- Added configurable Core API URL plus **Copy Hosted Push** and **Install
  Hosted Sync** actions to the Edge Settings console.
- Advanced API, agent, dashboard, installer examples, and release tests to
  `0.2.8`.

Validation:

- Core: 237 tests and 4 subtests passed; focused API/Edge tests passed; docs
  verifier, Bandit, fatal flake8 rules, dependency audit, and the Render
  Blueprint validator passed. A live Uvicorn smoke returned health/ready 200
  and protected workspace 401 without a credential.
- Core PR checks passed on Python 3.10/3.11 plus Trivy, Semgrep, Gitleaks,
  dependency, license, security, and Cloudflare preview checks.
- Edge bridge tests exercised a real loopback Edge export and Core import,
  owner-only bundle persistence, secret non-disclosure, hosted service install,
  overlap behavior, and non-loopback HTTP rejection.
- `./scripts/edge test`: 95 backend/agent tests and 25 frontend tests passed;
  the static production build completed and npm audit found zero
  vulnerabilities.
- Edge PR branch and pull-request CI runs `29248909572` and `29248916665`
  passed. Main CI run `29249073906` then repeated migrations, tests, audits,
  release inspection, PostgreSQL backup/restore, dashboard build, and clean
  generated-state checks on the merge commit.
- Release workflow `29249103680` published versioned and stable sensor archives,
  the standalone bootstrap, and SHA-256 manifests from the verified `v0.2.8`
  tag. GitHub artifact attestations remain unavailable for this user-owned
  private repository, so the verified release workflow publishes checksums.
- Render API deployment `dep-d9adcum8bjmc73aar24g` and scheduler deployment
  `dep-d9adcuu8bjmc73aar2bg` are live on exact merge `f554a78`. The public API
  reports version `0.2.8`, matching commit `f554a786b96a`, and ready schema
  revision `0012_integration_tokens`.
- Cloudflare Pages production deployment
  `4cf87d7a-3cb8-4822-ba52-b7993484249e` serves exact merge `f554a78` with the
  hosted Render API URL and dashboard demo mode disabled.
- Deployed Settings browser QA passed at desktop and `390x844`: both hosted Core
  actions were present, the copy action showed its explicit success state, the
  console was clean, no framework error rendered, and mobile had no horizontal
  overflow (`clientWidth == scrollWidth == 390`).

Known deployment boundary:

- Hosted Core is deploy-ready but not created. Render persistent disks require
  a paid web service, so activation remains an explicit cost decision. Local
  Core sync continues to work without that service.
- Canonical Mission Control authentication remains staged until an authorized
  Supabase database credential is available for the RLS migration and an
  invited operator is confirmed.

## Checkpoint 034 - Canonical Core and Edge Operator Boundary

Status: complete

Branch and merge:

- Dashboard PR: `#8` (`codex/canonical-core-edge-dashboard`)
- Dashboard merge: `3c11eb9e9555b9e0069310099204e89ea0a72a62`
- Dashboard security hotfix PR: `#9` (`codex/auth-disabled-fail-closed`)
- Dashboard security hotfix merge: `3b90aa5f923938afd8442b393b6500d45e881ea9`
- Dashboard release-hygiene PR: `#10` (`codex/dashboard-release-hygiene`)
- Dashboard release-hygiene merge: `2fdf61af25992a393a23a1a22eed49b8310c5f73`
- Cloudflare preview: `e9bcd48d-e44d-47d8-bef9-c0404933c8f3`
- Cloudflare production: `e9f92716-4f1d-487c-9112-df44556f2e46`

Completed changes:

- Added a server-side `/api/secopsai/edge-workspace` aggregate that reads the
  canonical Core workspace and live Edge operations without exposing Core,
  Edge, or operator credentials to browser JavaScript.
- Protected integration, SecOpsAI, run-output, and blog routes with the current
  Supabase operator session. A deployment with protected backend configuration
  now fails closed when dashboard authentication is disabled.
- Kept separate server-only Core read and Edge operations credentials, enforced
  HTTPS origins, rejected redirects, bounded responses, added upstream
  timeouts, and sanitized downstream failures.
- Fixed operator token refresh so a same-user `TOKEN_REFRESHED` event replaces
  the expired session before the dashboard reuses it.
- Scoped the Edge page to Edge-origin Core findings while retaining live Edge
  sites, sensors, schedules, jobs, and integration-token health. Synced Core
  graph nodes provide a fallback when the live Edge operations API is absent.
- Documented the Worker environment and secure activation sequence. Advanced
  the dashboard package to `1.2.1`.
- Closed a production rollout defect found during browser QA: an auth-disabled
  deployment could still initialize the configured Supabase client. The
  Worker now omits Supabase browser credentials, the app shows a dedicated
  locked deployment state, and no live workspace boot path runs while
  authentication is disabled.
- Ignored local `node_modules/` output created by Pages development tooling so
  browser validation no longer dirties the dashboard worktree.

Validation:

- Dashboard `npm run check` and `npm test` passed; the Python dashboard suite
  passed 41 tests and `git diff --check` passed.
- Tests prove anonymous protected routes return 401, backend configuration
  cannot be served with auth disabled, credentials stay out of returned JSON,
  downstream credentials remain separated, redirects are rejected, and
  refreshed operator sessions replace stale tokens.
- Cloudflare Pages built preview source `5142dbc` successfully. Browser QA at
  desktop and `390x844` showed the operator gate, a clean console, no framework
  overlay, and no horizontal overflow.
- Dashboard PR `#8` passed its Cloudflare Pages check and merged cleanly into
  `main`.
- Security hotfix PR `#9` passed Cloudflare Pages and merged. The auth-disabled
  Worker state was tested locally and on production at desktop and `390x844`:
  no Supabase browser configuration, no live workspace records, no console
  errors, and no horizontal overflow.
- Release-hygiene PR `#10` passed Cloudflare Pages and merged. Production
  deployment `e9f92716-4f1d-487c-9112-df44556f2e46` serves final merge
  `2fdf61a`.

Known activation boundary:

- The preview correctly reports that Supabase credentials are absent from the
  preview environment. Production operator access remains gated on applying
  the RLS migration, confirming an invited operator, and then enabling
  `DASHBOARD_AUTH_REQUIRED`.
- Hosted Core remains deploy-ready but unprovisioned because reliable SQLite
  requires a paid Render persistent disk. The dashboard route and tests are
  ready for that service when the cost is approved.

## Checkpoint 035 - Durable Account Recovery And Browser Workflows

Status: complete

Branch and release:

- Edge: `codex/account-recovery`
- Pull request: `#19`
- Merge commit: `31b3980052dd978c8c02988bb491dccbd27e84c6`
- Release: `v0.2.9`

Completed changes:

- Added durable one-time password-reset records with keyed token hashes,
  expiry, cooldown, retry/backoff, terminal delivery state, and no raw token at
  rest. Successful resets clear lockout state and revoke existing sessions.
- Added deliberately non-enumerating request and confirmation endpoints plus
  owner/admin delivery history, manual retry, and audit events.
- Added Settings recovery controls. Reset tokens arrive in the URL fragment,
  are removed immediately after capture, and are never exposed by delivery
  history APIs.
- Added operator-visible account-email delivery diagnostics and extended the
  five-minute scheduler to process due account-access deliveries.
- Added SMTP/reset URL deployment settings and production validation that
  requires a clean HTTPS reset URL whenever SMTP is enabled.
- Added migration `0013_account_recovery` and advanced the API, agent,
  dashboard, installer, release, and documentation baseline to `0.2.9`.
- Added Playwright desktop/mobile workflow coverage for dashboard login,
  password recovery, remote scan queueing, finding triage, schedule creation,
  and report generation. Browser tests use a disposable API contract and never
  scan a network or access production data.
- Added browser prerequisites to developer setup, CI, the release gate path,
  and generated-artifact release hygiene.

Validation before PR:

- Focused account recovery, auth, and production configuration tests passed:
  `19 passed`.
- Real PostgreSQL upgrade from `0012` to `0013` passed with no schema drift.
  A disposable PostgreSQL database also passed clean install, downgrade, and
  re-upgrade through `0013`.
- Full pre-browser suite passed with `99` backend/agent tests, `27` frontend
  component tests, a successful static production build, and zero npm audit
  vulnerabilities.
- Playwright passed all `8` workflow executions across desktop and mobile
  Chromium.

Merge, release, and deployment evidence:

- Pull-request CI runs `29255109320` and `29255112703` passed before merge.
  Main CI run `29255330493` then repeated migrations, backend/agent tests,
  dependency audits, release inspection, PostgreSQL backup/restore, the static
  dashboard build, `27` component tests, all `8` desktop/mobile browser
  workflows, and clean generated-state verification on the merge commit.
- Release workflow `29255994140` rebuilt and verified the exact tag, then
  published versioned and stable sensor archives, the standalone bootstrap,
  and SHA-256 manifests. GitHub artifact attestations remain unavailable for
  this user-owned private repository; the release workflow records that
  limitation explicitly and publishes checksums.
- Render API deployment `dep-d9aeprcvikkc73eatna0` and scheduler deployment
  `dep-d9aeprkvikkc73eatnlg` are live on exact merge `31b3980`. The public API
  reports version `0.2.9`, matching commit `31b3980052dd`, and readiness schema
  revision `0013_account_recovery`.
- Cloudflare Pages production deployment
  `2dcc86d7-4719-4350-8b3c-de4152e13633` serves source `31b3980` with the
  hosted Render API URL and dashboard demo mode disabled.
- Deployed Settings browser QA confirmed the account-recovery control, hosted
  API URL, explicit disconnected session state, no demo banner, no framework
  error, no desktop horizontal overflow, and a clean console. Mobile layout is
  covered by the exact-build Pixel 7 Playwright project; the in-app browser's
  temporary viewport override did not apply, so no separate deployed-mobile
  claim is made here.

Activation boundary:

- Render configuration has no contract drift, but the free pilot PostgreSQL
  database reports expiry on `2026-07-20`. A paid durable database or an
  explicit backup/migration decision is required before any customer pilot.
- Hosted password-reset email requires approved SMTP credentials and the
  deployed Cloudflare Settings URL. The application safely records retrying or
  failed delivery state when those values are absent; no email provider or paid
  service is provisioned automatically.
- Optional MFA, invitation acceptance, recovery codes, enrollment/PDF browser
  workflows, and automated accessibility checks remain subsequent checkpoints.

## Checkpoint 036 - Operator Invitations And MFA

Status: complete

Branch, merge, and release:

- Edge: `codex/operator-invitations-mfa`
- Pull request: `#21`
- Feature commit: `e84db3d9b368ffea7abbaaa277b30036264cb6be`
- Merge commit: `90ab7223ed26fc1e03cfe4156b25b934639f45d9`
- Release: `v0.3.0`

Completed changes:

- Replaced normal administrator-created temporary passwords with durable,
  one-time operator invitations. New operators choose their own password;
  existing operators prove their current password before gaining another
  workspace membership.
- Added pending-invitation listing/revocation, invitation delivery diagnostics,
  supersession, expiry, one-time acceptance, audit events, and shared account
  email retry processing.
- Fixed disabled and not-yet-activated accounts so login fails before any
  dashboard session is issued.
- Made dashboard bootstrap create-once: deploys no longer overwrite an
  existing password, promote a user, or reactivate a disabled account.
- Added optional RFC 6238 TOTP MFA, short-lived signed login challenges,
  encrypted TOTP secrets, replay protection, one-use hashed recovery codes,
  recovery-code replacement, MFA disablement, and session revocation after
  security-boundary changes.
- Added row locking for one-time account links, login counters, TOTP replay
  state, and recovery-code consumption. Existing MFA cannot be replaced without
  first proving the current factor; a different workspace owner has an audited
  reset action for genuine factor-loss recovery.
- Separated the AES-GCM MFA encryption key from the dashboard session token
  secret so an ordinary token-secret rotation cannot silently invalidate
  enrolled authenticators.
- Added shared lockout and audit handling for existing-account invitation
  password attempts.
- Added migration `0014_operator_access`, advanced the API, agent, dashboard,
  installer, release checks, and documentation baseline to `0.3.0`, and added
  the required Render invitation/MFA configuration contract.
- Reworked Settings > Users & Sessions around invitations, pending delivery,
  authenticator setup, one-time recovery-code display, and MFA status. Login
  now completes the MFA challenge before persisting a browser session.
- Expanded component and desktop/mobile browser workflows for invitation
  acceptance and MFA challenge login.

Validation:

- A real PostgreSQL migration upgraded `0013_account_recovery` to
  `0014_operator_access`, passed `alembic check`, downgraded one revision, and
  upgraded again successfully.
- Focused invitation/MFA API tests, existing auth/account tests, frontend
  component tests, the static Next.js build, and 12 desktop/mobile Playwright
  workflow executions passed during implementation.
- The final `./scripts/edge test` working-tree gate passed with `107`
  backend/agent tests, `30` frontend component tests, the Next.js production
  static build, all `12` desktop/mobile browser workflows, and zero npm audit
  vulnerabilities.
- `pip-audit -r requirements.lock` found zero known vulnerabilities after the
  security review replaced vulnerable `cryptography 46.0.5` with the compatible
  fixed `48.0.1` wheel.
- The checked-in Render Blueprint passed provider validation. Live API,
  scheduler, and PostgreSQL contracts have no drift; the free database expiry
  on `2026-07-20` remains the only operational warning.
- A targeted security diff review added transaction locks around one-use
  account/MFA state, separated encryption/session key lifecycles, blocked MFA
  replacement without the current factor, added owner-assisted audited
  recovery, and made dashboard bootstrap create-once.
- Pull-request CI runs `29260678514` and `29260697479` passed before merge.
  Main CI run `29260973779` then repeated migrations, `107` backend/agent
  tests, dependency audits, release inspection, PostgreSQL backup/restore, the
  dashboard build, `30` component tests, all `12` desktop/mobile browser
  workflows, and generated-state verification on the exact merge commit.
- Release workflow `29261200368` rebuilt and verified the tag before publishing
  the versioned/stable archives, bootstrap, and SHA-256 manifests at
  `https://github.com/Techris93/secopsai-edge/releases/tag/v0.3.0`.

Deployment evidence:

- Render API deployment `dep-d9afurj7uimc73fkibr0` and scheduler deployment
  `dep-d9afurr7uimc73fkic2g` are live on exact merge `90ab7223`. Public health
  reports API `0.3.0`, commit `90ab7223ed26`, and readiness schema
  `0014_operator_access`.
- Cloudflare Pages production deployment
  `b9e2aa7f-29d9-4209-ad55-b812b506644c` serves source `90ab722` with the
  hosted Render API and dashboard demo mode disabled.
- Deployed Settings browser QA confirmed the correct hosted API, explicit
  disconnected state, no demo banner, no framework error, no desktop
  horizontal overflow, and a clean console. The exact-build mobile Chromium
  project covers the invitation and MFA login workflows.

Activation boundaries:

- SMTP invitation/reset delivery remains inactive until an approved provider
  is configured and exercised without exposing credentials.
- A second owner account, stored recovery codes, and an owner-assisted MFA
  reset exercise are required before external pilot access.
- The free Render PostgreSQL database expires on `2026-07-20`; durable paid
  storage or an explicit backup/migration decision remains a controlled-pilot
  blocker and is not made durable by this checkpoint.

## Checkpoint 037 - Accessibility And Browser Completion

Status: complete

Completed changes:

- Added automated axe-core WCAG 2.0/2.1 A and AA checks for all ten principal
  operator routes in desktop Chromium and the Pixel 7 profile.
- Added production-build browser workflows for one-time sensor enrollment,
  installer command copy/dismiss/revoke, authenticated PDF download, keyboard
  skip navigation, current-page semantics, responsive overflow, and explicit
  empty, API-unavailable, and deployment-degraded states.
- Added a keyboard-visible skip link, global focus treatment, current-page
  navigation semantics, accessible names for operational controls, and
  keyboard access to horizontally scrollable evidence and data tables.
- Corrected medium-severity color contrast and removed the false no-data flash
  that appeared before the first API response.
- Added actionable empty states for assets, findings, Wi-Fi networks, reports,
  and sites without confusing loading or unavailable states with empty data.
- Kept browser tests on a disposable in-process API contract; no production
  account, sensor, network scan, or raw telemetry is touched.
- Advanced the current product and release baseline to `0.3.1`.

Branch:

- Edge: `codex/accessibility-browser-completion`
- Pull request: `#23`
- Feature commit: `e409d13419f2836c8e2f101079b34b37782822f3`
- Merge commit: `8fb3c17256cf92dfcbbf083c9637d036f063f618`
- Release: `v0.3.1`

Validation before PR:

- `./scripts/edge test` passed with `107` backend/agent tests, `30` frontend
  component tests, a successful static production build, all `24`
  desktop/mobile browser workflows, and zero npm audit vulnerabilities.
- Automated WCAG checks passed across Overview, Onboarding, Sites, Assets,
  Wi-Fi, Findings, Schedules, Reports, Audit Log, and Settings in both browser
  projects.
- Focused `0.3.1` worker/release-distribution tests and all component tests
  passed after the version advance.
- `pip-audit -r requirements.lock` found zero known Python dependency
  vulnerabilities.
- `git diff --check` passed.
- Pull-request checks `29264374317` and `29264376371` passed. Main-branch CI
  run `29264635334` passed after the merge.
- Release workflow `29264883933` published the private `v0.3.1` GitHub release
  with versioned and stable archives, bootstrap installer, and SHA-256
  manifests. The release archive digest begins `e8d7ae` and was checked against
  the exact merge commit.
- Render API deploy `dep-d9agnb6q1p3s73dkfo8g` and scheduler deploy
  `dep-d9agnbeq1p3s73dkfomg` became live at the exact merge commit. `/healthz`
  reported version `0.3.1` and commit `8fb3c17256cf`; `/readyz` reported schema
  revision `0014_operator_access`.
- Cloudflare production deployment `70a8e224-d8d1-46d0-9065-99c19b161640`
  published source `8fb3c17` with demo mode disabled and the Render API base URL.
- A deployed-browser Settings check confirmed the canonical Cloudflare URL,
  hosted API URL, explicit disconnected state, no demo banner, no framework
  error or console error, and a working Refresh interaction. The exact static
  build had already passed all `24` desktop/mobile browser workflows, including
  responsive-overflow and accessibility coverage.

Remaining boundary:

- Automated checks reduce regression risk but do not replace a manual
  assistive-technology review with VoiceOver/NVDA before broad commercial use.
- Checkpoint `038` still owns durable hosted storage, backup/restore, retention,
  uptime, and real operator recovery proof.

## Checkpoint 038 - Durable Pilot Operations

Status: implementation and release complete; external pilot activation gated

Completed changes:

- Added migration `0015_data_lifecycle` and organization-scoped retention
  policies for normalized observations, scan history, notification deliveries,
  account-access records, expired credential metadata, reports, and audit logs.
- Added a once-per-24-hours retention runner to the existing five-minute
  scheduler plus an explicit administrator **Run cleanup** action in Settings.
- Added versioned `secopsai.edge.site-export.v1` customer exports, including
  minimized notification-delivery and site-scoped audit history. Raw
  observation payloads, token hashes, account/MFA material, integration
  credentials, notification payload/response bodies, destinations, and
  endpoint error text are excluded; secret-shaped audit fields are redacted.
- Added owner-only site deletion with active-job protection, exact-name and
  permanent-action confirmation, current-password proof, MFA proof when
  enabled, ordered transactional deletion, and a minimal post-deletion audit
  record.
- Added Settings data-lifecycle controls and clickable site Export/Delete
  workflows with explicit success/error states.
- Added `./scripts/edge cloud uptime-check` and an opt-in six-hourly GitHub
  monitor that records non-secret API liveness, database/schema readiness,
  dashboard availability, latency, release, and commit evidence.
- Removed duplicate full CI execution on feature-branch pushes. Pull requests
  retain the complete verification gate and `main` retains post-merge proof.
- Documented the 99.5% controlled-pilot readiness target, four-hour
  service-blocking response target, pilot export/deletion flow, and two-owner
  recovery exercise.
- Advanced the application, agent, dashboard, installer, migration, and release
  baseline to `0.3.2`.

Branch:

- Edge: `codex/durable-pilot-operations`
- Pull request: `#25`
- Feature commit: `11ba78f89b66ce5b72e10b836ef5d8e844f38e3d`
- Merge commit: `9c7bf4db5e6507cd5cec89822acd2701a2628a18`
- Release: `v0.3.2`

Implementation validation:

- Site export tests prove workspace isolation and exclusion of raw payloads,
  token hashes, and private notification targets.
- Deletion tests cover legacy-token rejection, exact confirmation, active-job
  blocking, password proof, MFA enforcement, ordered deletion, and retained
  minimal audit evidence.
- Retention tests cover configurable policies, tenant isolation, recent-record
  preservation, expired-record removal, and the 24-hour due-run guard.
- Hosted-health tests cover successful evidence recording and degraded
  readiness failure without storing response bodies.
- Local product gate passed with `112` backend/agent tests, `32` frontend
  component tests, `28` desktop/mobile browser workflows, a production static
  build, automated WCAG A/AA checks, and `0` npm audit vulnerabilities.
- `./scripts/release-gate` passed at the feature commit and verified migration
  head `0015_data_lifecycle`, the complete test/build/audit suite, release
  archive contents, and archive checksum.
- Pull-request CI runs `29268475422` and `29268492081` passed. Main-branch CI
  run `29268758557` passed on the exact merge, including the PostgreSQL
  migration/schema-drift exercise, matching-major backup/restore drill,
  Python dependency audit, dashboard build, and browser matrix.
- Release workflow `29269017675` published the private `v0.3.2` GitHub release
  from the exact merge. The downloaded versioned archive matched its SHA-256
  manifest; its digest is
  `3d65a4be99ac7e310f72fc31dc50defbab909b62aa428a11bebc5b77cd015582`.
- Render API deploy `dep-d9ahjjt8nd3s73ch4tg0` and scheduler deploy
  `dep-d9ahjkd8nd3s73ch4u90` became live on the exact merge. `/healthz`
  reported version `0.3.2` and commit `9c7bf4db5e65`; `/readyz` reported schema
  revision `0015_data_lifecycle`.
- Cloudflare production deployment
  `5fc83a67-259b-4a75-aa7f-70f5b320050b` published source `9c7bf4d` with demo
  mode disabled and the hosted Render API URL. A deployed-browser Settings
  check confirmed the new Data Lifecycle panel and hosted-health command
  controls on the canonical Pages URL.
- The current workstation's shell resolver timed out for `pages.dev` during a
  CLI availability probe even though Cloudflare reported the deployment live
  and the in-app browser loaded the canonical URL. The independent monitor
  required before a paid pilot must run from a separate provider/network so a
  local DNS path cannot mask or invent availability.

Activation boundaries:

- The current Render API and PostgreSQL remain free demo resources. Render
  states that free web services spin down and free PostgreSQL expires after 30
  days without backups. An account owner must approve recurring cost and move
  both resources to paid instance types before external pilot data is accepted.
- After upgrade, perform Render point-in-time recovery into a separate database
  and record the recovery time and validation evidence. The existing matching-
  major logical backup/restore remains a second recovery path.
- Configure an approved email provider, enroll a second real owner, and execute
  the invitation, MFA, recovery-code, owner-reset, and re-enrollment drill. Test
  coverage cannot substitute for this operator exercise.
- The opt-in six-hour GitHub monitor is coarse controlled-pilot evidence, not a
  contractual SLA monitor. Paid pilots require an independent five-minute
  monitor and named escalation contact.

## Completion Rules

A checkpoint is complete only when:

- Code or docs changed in the checkpoint are listed here.
- Tests or validation commands are recorded.
- Known risks and next tasks are updated.
- The repo status is checked and summarized.

## Checkpoint 039 - Research And Wireless Operational Boundary

Status: complete; external pilot activation remains gated

Scope:

- Keep Wi-Fi collection metadata-only and platform-explicit. Do not add packet
  capture, monitor mode, injection, deauthentication, or other active wireless
  operations to the pilot sensor.
- Add Linux `iw` inventory with interface selection, capability diagnostics,
  dBm/channel normalization, and explicit unsupported/permission failures.
- Preserve Wi-Fi source/interface provenance through Edge storage and Core
  export without sending raw scan output to AI or Core.
- Make independent research case exports reproducible and auditable.
- Add safe local artifact hash-only evidence and a guided package-case start
  flow for defensive, public-source research.

Completed changes:

- Added `LinuxIwWifiScanner`, `wifi-status`, managed-mode `iw` collection,
  `SECOPSAI_WIFI_INTERFACE` support, and explicit `CAP_NET_ADMIN` guidance.
- Added macOS legacy `airport` capability reporting and clear boundaries around
  the absence of supported monitor-mode collection on current macOS.
- Added Wi-Fi `source` provenance to normalized API models, detection records,
  Core export, dashboard cards, sample data, and migration `0016_wifi_provenance`.
- Added Core research export schema
  `secopsai.research.case.v1` and checksum manifest schema
  `secopsai.research.export-manifest.v1`. JSON, Markdown, and manifest output
  is byte-stable for an unchanged case.
- Added `secopsai research case add-artifact`, which hashes a regular local file
  through a bounded stream, rejects symbolic links and oversized files, stores
  no absolute path, and never executes or unpacks the artifact.
- Added `secopsai research case start-package`, which creates a draft package
  case, records analyst-supplied public source metadata, and optionally hashes
  a local artifact without fetching or executing it.
- Added research-case tests, wireless parser/capability tests, provenance
  coverage, and the defensive research workflow documentation.

Validation:

- Edge `./scripts/edge test`: `119` backend/agent tests, `32` frontend tests,
  production static build, browser matrix, accessibility checks, and zero npm
  audit vulnerabilities passed.
- Core `.venv/bin/python -m pytest tests`: `239` tests passed. Research-focused
  tests cover deterministic exports, checksum manifests, symlink rejection,
  hash-only evidence, and guided package starts.
- `./scripts/edge wifi status` completed on this macOS host using the explicit
  `macos:airport` capability path. No network scan or physical adapter claim
  was made.
- `git diff --check`, Python compilation, shell syntax, and migration-head
  checks passed during implementation.

Known boundaries:

- Physical TL-WN722N V4 behavior remains hardware/chipset/driver dependent and
  requires an authorized Linux pilot validation; it is not represented as
  tested by fixture-only parser coverage.
- The macOS `airport` path is a legacy metadata inventory boundary. A modern
  macOS passive/monitor-mode sensor is not claimed by this checkpoint.
- Paid Render storage, independent uptime monitoring, and pilot operator
  exercises remain checkpoint 040/041 work.

Next checkpoint:

- Execute the external pilot acceptance matrix, including a real Linux sensor
  validation where hardware is available, hosted recovery/backup proof, and
  independent availability evidence.

## Checkpoint 040 - External Pilot Acceptance Preparation

Status: implementation complete; external operator acceptance pending

Scope:

- Turn the acceptance matrix into a repeatable, non-destructive command and
  evidence record.
- Make the remaining external boundaries explicit instead of allowing a green
  local test suite to imply paid hosting, hardware, notification, or recovery
  validation.

Completed changes:

- Added `./scripts/edge pilot check [--cloud] [--output FILE]` and the JSON
  schema `secopsai.edge.pilot-acceptance.v1`.
- Required checks cover Nmap/Python, hosted liveness/readiness, dashboard
  reachability, and the local worker service. Wi-Fi capability is an advisory
  unless `--require-wifi` is selected.
- The acceptance record stores only status, latency, release/schema identity,
  and error types. It excludes HTTP bodies, tokens, notification payloads,
  package contents, and scan output.
- Added the Settings copy-command button, pilot acceptance documentation, and
  the operator matrix for fresh install, schedule, notifications, recovery,
  support, seven-day soak, and pilot exit.

Validation:

- `./scripts/edge test`: `121` backend/agent tests, `32` frontend tests,
  production static build, `28` desktop/mobile browser workflows, accessibility
  checks, and zero npm audit vulnerabilities passed.
- Focused pilot acceptance tests passed (`4`), including hosted readiness
  failure handling and the no-response-body boundary.
- Release gate passed on Edge merge `9084569`; tag `v0.3.3` release workflow
  `29273025383` completed successfully.
- Live hosted API check reported Edge `0.3.3`, commit `9084569708bb`, readiness
  schema `0016_wifi_provenance`, and HTTP 200 for `/healthz` and `/readyz`.
- The current host has Nmap and Python available. No matching TL-WN722N USB
  device was visible in the read-only USB inventory check.

External acceptance still required:

- Switch Render API/PostgreSQL to paid plans and perform a provider PITR
  restore into a separate database.
- Configure and exercise one approved notification provider and destination.
- Enroll a second real workspace owner and complete MFA/recovery/reset proof.
- Install the release on a fresh authorized host, keep the worker running for a
  seven-day soak, and perform the schedule/offline-sensor/change-detection
  exercises.
- Validate TL-WN722N V4 on the actual supported Linux/Raspberry Pi host if
  wireless inventory is part of the pilot scope.
- Resolve the current shell DNS timeout for the `pages.dev` dashboard or record
  an independent monitor that can reach the canonical Pages URL. The API is
  healthy; this is not being treated as dashboard availability proof.

Next checkpoint:

- Complete the external operator matrix and produce a signed pilot go/no-go
  record, then perform checkpoint 041 release closeout.

## Checkpoint 041 - Controlled Pilot Release Closeout

Status: implementation and release complete; external operator acceptance remains pending

Scope:

- Close the controlled-pilot implementation sequence against an exact verified
  main-branch build.
- Publish the installable release artifact and record hosted release identity.
- Align the operator README, pilot acceptance guide, roadmap, and release
  evidence with the actual deployed version.

Completed evidence:

- Edge main is clean at merge commit `3d04757edd54e2244eec34d6bfce68bad9cf106d`.
- Tag `v0.3.4` is published from that exact main commit.
- Post-merge main CI run `29274537014` passed all `28` checks, including
  migrations, `121` backend/agent tests, release inspection, backup/restore,
  dashboard install/build, and generated-state hygiene.
- Release workflow `29274806138` published the GitHub release and versioned
  bootstrap/archive assets. Private-repository artifact attestations are not
  available for this repository, so the verified workflow publishes SHA-256
  manifests instead.
- The downloaded `secopsai-edge-0.3.4.tar.gz` matched its published SHA-256
  manifest.
- Hosted Render `/healthz` reports version `0.3.4` and commit `3d04757edd54`.
  Hosted `/readyz` reports version `0.3.4` and schema revision
  `0016_wifi_provenance`.
- Cloudflare Pages production deployment `9b3b0920-352d-467f-bbd8-3e7d1606b907`
  is attached to Edge main `8f8d52d` and contains the current dashboard build.
- README, install, pilot acceptance, roadmap, architecture, runbook, and
  dashboard Settings guidance now point at the current pilot workflow and
  release version.

Acceptance boundary:

- The current host's direct acceptance record passed Nmap, Python, hosted
  liveness, and hosted readiness. Its dashboard check was inconclusive because
  this host timed out resolving both the canonical and deployment Pages
  hostnames; Cloudflare accepted the deployment, but no browser availability
  claim is made from this network.
- Checkpoint 040 remains implementation-complete but operator-pending. Before
  external customer data is accepted, the owner must still complete paid
  Render API/PostgreSQL activation with an isolated PITR drill, exercise a real
  notification destination, enroll a second owner and complete MFA/recovery,
  run the fresh-host seven-day soak, and validate Linux/Raspberry Pi wireless
  hardware if Wi-Fi is in scope.
- These are external activation and evidence gates, not unimplemented product
  code. They must be recorded in a signed pilot go/no-go record rather than
  inferred from local tests.

Validation:

- Edge local release gate passed before merge; post-merge CI passed again on the
  exact release commit.
- Release archive download and checksum verification passed.
- Hosted health/readiness verification passed after deployment.

Next checkpoint:

- Complete the external operator acceptance matrix and record a signed pilot
  go/no-go decision. Do not claim the controlled pilot is customer-ready until
  the paid infrastructure, second-owner recovery, notification, fresh-host soak,
  and any in-scope wireless evidence are attached.

## Checkpoint 042 - AI Report Cost Guardrail

Status: complete

Scope:

- Bound report-generation cost and provider pressure at the API boundary.
- Make the active guardrail visible to authenticated operators.
- Validate configuration errors instead of silently accepting unsafe values.

Completed changes:

- Added `AI_REPORT_COOLDOWN_SECONDS`, defaulting to five minutes and scoped per
  site. A repeated report request returns HTTP 429 with `Retry-After`.
- Kept `AI_MAX_FINDINGS_PER_REPORT` as an explicit positive bound and exposed
  both AI guardrail values through `/api/v1/system/status`.
- Added the guardrail summary to the dashboard System Health panel.
- Documented production configuration and the controlled-test-only meaning of
  a zero cooldown.

Validation:

- Focused API/config tests passed, including invalid guardrail values and the
  repeated-report 429 contract.
- Full Edge validation passed: `123` backend/agent tests, `32` frontend tests,
  `28` desktop/mobile browser workflows, production build, accessibility
  checks, and zero npm audit vulnerabilities.
- Release gate passed on merge commit `7fcd9eafee780340d0ddc6b5540b4254b230a1e1`.
- Tag `v0.3.5` and release workflow `29278453261` published the verified
  archive and SHA-256 manifest; the downloaded archive checksum matched.
- Render `/healthz` reports version `0.3.5` and commit `7fcd9eafee78`.
  Render `/readyz` reports version `0.3.5` and schema revision
  `0016_wifi_provenance`.
- Cloudflare Pages production deployment
  `bd4c726f-7d2f-4d24-811e-b4ee75d5cd7b` is attached to Edge main commit
  `7fcd9ea`.

Acceptance boundary:

- Keep the external pilot acceptance gates from Checkpoint 040 open until
  paid infrastructure, notification, account recovery, fresh-host soak,
  wireless scope, and independent dashboard availability evidence are complete.

Next checkpoint:

- Re-audit the main Core, unified Dashboard, and OpenClaw integration surfaces
  for the next code-completable product gap. Do not infer customer readiness
  from hosted health alone.

## Checkpoint 043 - Cross-Product Sync Freshness

Status: complete

Scope:

- Make Edge-to-Core synchronization freshness visible to Core operators and
  local automation.
- Keep the status surface read-only and limited to normalized lifecycle
  metadata.
- Record the merged cross-repository implementation and verification evidence.

Completed changes:

- Core now exposes `secopsai edge status` with human-readable and JSON output
  for recent source identity, contract version, bundle timestamp, local sync
  timestamp, and cursor records.
- OpenClaw now exposes the read-only `secopsai_edge_sync_status` tool using the
  canonical Core CLI contract.
- Core integration documentation and this Edge ledger now describe the shared
  freshness signal and its raw-telemetry boundary.

Evidence:

- Core PR #40 merged to `main` as `63e3f1a`; full Core suite passed with
  `239` tests.
- OpenClaw plugin PR #2 merged to `master` as `20fa060`; TypeScript build and
  both plugin contract tests passed.
- The canonical Dashboard already exposes the corresponding Edge-to-Core
  freshness state from Core workspace data in production deployment
  `ddbba4b9-e9fd-48ec-ab74-f660875f1839`.
- Edge roadmap alignment remains merged in `2c266ce`, with controlled release
  work through checkpoint 042 and external pilot acceptance gates still open.

Acceptance boundary:

- This checkpoint proves the code and contract surfaces. It does not replace
  the external paid-infrastructure, notification, second-owner recovery,
  fresh-host soak, wireless hardware, or independent dashboard-availability
  evidence required by the controlled pilot acceptance record.

Next checkpoint:

- Continue the code-completable pilot-hardening audit with the highest-impact
  remaining gap, while keeping the external acceptance matrix separate from
  implementation claims.

## Checkpoint 044 - Safe OpenClaw Edge Operator Tools

Status: complete

Scope:

- Give the OpenClaw local automation bridge useful Edge control-plane
  visibility without bypassing scan authorization or service safeguards.
- Keep direct Edge mutations outside this read-only checkpoint.
- Record the configuration, safety boundary, and contract evidence.

Completed changes:

- Added configurable `edgePath` support to the OpenClaw plugin, defaulting to
  `~/secopsai-edge`.
- Added `secopsai_edge_worker_status`, which reads local launchd/systemd worker
  state without starting or stopping the service.
- Added `secopsai_edge_scan_preview`, which accepts a private IPv4 CIDR and
  prints Edge's safe Nmap plan without running a scan or uploading telemetry.
- Added structured `execFileSync` execution with a bounded timeout and output
  buffer for the Edge helper, plus contract tests using a fake Edge install.
- Updated the platform roadmap and plugin operator documentation.

Evidence:

- OpenClaw PR #3 merged to `master` as `4135856`; `npm test` passed with the
  TypeScript build and both plugin contract tests.
- The Edge worker status command was exercised on this host and reported the
  expected non-running service state without mutating it.
- The Edge repository post-merge CI for checkpoint 043 passed all `28` checks;
  this checkpoint changes documentation only in Edge and will use the same
  repository gate before merge.

Safety boundary:

- The plugin does not expose Edge scan execution, service start/stop, token
  rotation, or credential output in this checkpoint.
- The CIDR schema narrows inputs to RFC1918 private IPv4 ranges, while the Edge
  agent remains the final authority for prefix and host-count limits.
- The Edge helper is invoked with structured argv, a 30-second timeout, and a
  1 MiB output cap; no shell command string is constructed.

Acceptance boundary:

- This checkpoint improves local automation ergonomics but does not close the
  external paid-infrastructure, notification, second-owner recovery,
  fresh-host soak, wireless hardware, or independent dashboard-availability
  gates from checkpoint 040.

Next checkpoint:

- Reassess whether approval-gated Edge scan/report actions are required for the
  pilot, then continue the external operator acceptance matrix rather than
  treating read-only automation as customer readiness.

## Checkpoint 045 - Research Ecosystem Contract Alignment

Status: complete

Scope:

- Remove the mismatch between the Core research engine and its OpenClaw
  surface.
- Make NuGet-style and other supported package investigations available through
  the same documented plugin contract.
- Add regression coverage so a future Core ecosystem addition is visible in
  the plugin review rather than silently rejected by its schema.

Completed changes:

- OpenClaw `secopsai_research_package` and
  `secopsai_review_release_with_sources` now advertise all twelve Core
  ecosystems: Chrome Web Store, crates.io, GitHub, Go, Hugging Face, Maven,
  npm, NuGet, Open VSX, Packagist, PyPI, and RubyGems.
- Added a contract test that invokes NuGet package research with the exact
  structured Core CLI arguments.
- Added the Braintree-style NuGet example to plugin documentation.

Evidence:

- OpenClaw PR #4 merged to `master` as `35983bf`.
- `npm test` passed after the schema and contract changes.
- Core's authoritative ecosystem registry currently contains the same twelve
  names used by the plugin.

Acceptance boundary:

- This aligns the research interface; it does not claim that every ecosystem
  has identical live metadata or artifact availability. Core's per-ecosystem
  capability and limitation metadata remains authoritative, and static
  analysis stays non-executing by default.
- The external pilot gates from checkpoint 040 remain open.

Next checkpoint:

- Continue the product audit with approval-gated Edge actions or the next
  highest-impact pilot gap, while preserving the research safety boundary.

## Checkpoint 046 - Approval-Gated Edge Scan Actions

Status: implementation complete; external pilot acceptance remains pending

Scope:

- Give OpenClaw a useful Edge write path without allowing an AI tool to run
  Nmap, start services, or receive sensor credentials directly.
- Reuse Core's existing session and approval model as the audit boundary.
- Queue remote work for the local Edge worker rather than moving LAN access to
  Core or the hosted API.

Completed changes:

- Added Core `secopsai.edge_actions` validation for RFC1918 IPv4 `/24` or
  narrower targets and a bounded structured subprocess wrapper for the Edge
  queue helper.
- Added `edge_scan` custom approval payload handling to `session request-approval`
  and `session resolve-approval --apply`, with normalized session events and
  blocked-step diagnostics on queue failure.
- Added `./scripts/edge queue <cidr> --cloud [--wifi] [--sensor-id ID]`, which
  validates the target again, uses the saved scoped cloud credential, and
  creates an authenticated remote job without running discovery in Core.
- Added OpenClaw `secopsai_edge_request_scan` and passed the configured Edge
  root into the existing approval resolver.
- Documented the approval flow and the strict raw-telemetry/credential
  boundary across Core, Edge, and the plugin.

Validation:

- Core focused session/action tests: `9` passed, including rejection of public
  and broad CIDRs, structured helper arguments, approval application, and raw
  output exclusion.
- OpenClaw `npm test`: TypeScript build and plugin contract tests passed.
- Edge shell syntax validation: `bash -n scripts/edge` passed.
- Full Edge API scan-job regression tests: `7` passed.

Safety boundary:

- OpenClaw only requests approval; it cannot execute Nmap directly.
- Core accepts only normalized private IPv4 targets and never persists helper
  stdout/stderr.
- The Edge helper performs the same target restriction and reads its own local
  credential files; no token is placed in Core arguments or session records.
- Worker start/stop, token rotation, and report generation remain separate
  approval-gated work items.

Next checkpoint:

- Complete full cross-repository validation and merge this checkpoint, then
  continue the external pilot acceptance matrix and remaining commercial
  operations rather than treating approval-gated automation as customer
  readiness.

## Checkpoint 047 - Approval-Gated Edge Operations

Status: implementation complete; external pilot acceptance remains pending

Scope:

- Complete the remaining explicit OpenClaw Edge operator actions without
  weakening the approval and local-execution boundary.
- Add report generation and worker lifecycle control as auditable Core session
  payloads.

Completed changes:

- Added Core validation and bounded structured helper execution for
  `edge_report` and `edge_worker` payloads.
- Restricted worker operations to `start` and `stop`; arbitrary Edge commands
  are rejected before subprocess execution.
- Added OpenClaw `secopsai_edge_request_report` and
  `secopsai_edge_request_worker_action` tools. Both only create pending Core
  approvals; `secopsai_session_resolve_approval` remains the apply boundary.
- Added failure events, blocked session steps, successful operation events, and
  raw-helper-output exclusion coverage.
- Updated Core and plugin operator guides with report/worker examples and the
  credential boundary.

Validation:

- Core focused action/session tests: `10` passed.
- OpenClaw `npm test`: TypeScript build and plugin contract tests passed.
- Edge `./scripts/edge test`: `125` backend/agent tests, `32` frontend tests,
  `28` desktop/mobile browser workflows, production build, and zero npm audit
  vulnerabilities passed before this documentation-only Edge checkpoint.
- Core docs command and plugin-tool contract verification remain required at
  merge.

Safety boundary:

- Report output is discarded by Core; the report remains in Edge's authenticated
  report store.
- Worker lifecycle actions are an explicit two-value allowlist.
- No Edge credential, raw Nmap output, packet data, or helper stdout/stderr is
  persisted in Core sessions.

Next checkpoint:

- Merge the cross-repository changes, then audit token rotation, notification
  delivery, and external pilot activation evidence as the remaining product
  readiness work.

## Checkpoint 048 - Sensor Credential Recovery CLI

Status: complete; external pilot acceptance remains pending

Scope:

- Close the remaining operator-recovery gap between the dashboard token-rotation
  endpoint and the documented sensor-host CLI workflow.
- Ensure a lost or suspected sensor credential can be replaced without manual
  file editing or leaving a partially written secret file.

Completed changes:

- Added `./scripts/edge cloud rotate-sensor-token [sensor-id]` and the
  `./scripts/edge cloud reauth [sensor-id]` alias.
- The helper uses the hosted administrator credential only for the rotation
  request, validates that the API returned the requested sensor identity, and
  never prints the replacement secret.
- Replaced `.cloud-sensor.env` atomically through a same-directory temporary
  file with mode `0600`, and applied the same protection to fresh local/cloud
  registration output.
- Added `./scripts/edge worker restart` so the running service can load the
  replacement credential through a documented command.
- Added regression tests for rotation, alias handling, API argument shape,
  secret non-disclosure, atomic output, and file permissions.

Validation required before merge:

- `bash -n scripts/edge`.
- Focused CLI rotation tests.
- Full `./scripts/edge test` including frontend/browser/build/audit gates.
- Documentation and checkpoint consistency review.

Validation:

- `bash -n scripts/edge` passed.
- Focused rotation and queue regression tests passed.
- Full backend/agent suite passed: `127` tests.
- Full frontend suite passed: `32` tests.
- Production dashboard build passed.
- Both desktop/mobile principal-route accessibility workflows passed after
  increasing only that test's timeout for the ten-route Axe analysis.
- Full browser matrix passed: `28` workflows.
- Frontend dependency audit passed with zero vulnerabilities.
- Edge PR `#40` merged to `main` at `ffdb304`, and the verified `v0.3.6`
  archive, checksum, and bootstrap installer were published at the GitHub
  release page.

Safety boundary:

- The CLI does not expose the replacement token in stdout or logs; the worker
  reads it from the owner-only local credential file after restart.
- The rotation endpoint remains admin-authenticated and workspace-scoped.
- No scan, packet capture, or raw telemetry is involved.

Next checkpoint:

- Merge this recovery improvement, then close the remaining external pilot
  evidence gates and audit commercial SaaS/MSP, research-publication, and
  hardware lifecycle gaps separately.

## Checkpoint 050 - Hosted Health Failure Diagnostics

Status: complete; external pilot acceptance remains pending

Scope:

- Make the non-destructive pilot and uptime checks actionable when a hosted API
  or dashboard cannot be reached.
- Preserve the strict rule that health evidence never stores response bodies,
  credentials, or provider error text.

Completed changes:

- Added stable non-secret error codes for DNS resolution failures, network
  timeouts, HTTP failures, invalid JSON, and generic check failures.
- HTTP errors retain only the status code; URL error reasons and response bodies
  are intentionally excluded.
- Added tests for DNS and HTTP classification plus the existing success and
  degraded-readiness cases.
- Updated pilot acceptance and operator runbook guidance with recovery paths.

Validation:

- Focused hosted-health and pilot-acceptance tests passed: `6` tests.
- Python compilation and diff checks passed.
- The current hosted evidence classified the Pages failure as DNS reachability
  without recording a response body or resolver detail.
- Full Edge release gate passed at merge commit `2bafb40`:
  `129` backend/agent tests, `32` frontend tests, `28` desktop/mobile browser
  workflows, production build, npm audit, archive checksum, and credential-path
  checks.
- Release [`v0.3.7`](https://github.com/Techris93/secopsai-edge/releases/tag/v0.3.7)
  was published with the versioned archive, checksum, and bootstrap installer.

Next checkpoint:

- Continue the external acceptance matrix and commercial product tracks without
  treating local green tests as proof of hosted dashboard availability.

## Checkpoint 052 - Authenticated Pilot Evidence

Status: released; external pilot acceptance remains pending

Scope:

- Strengthen the non-destructive pilot acceptance command so it can verify a
  real operator credential and the authenticated product surfaces before an
  external user is invited.
- Keep credentials, response bodies, and customer telemetry out of the
  evidence record.

Completed changes:

- Added an optional `SECOPSAI_PILOT_ACCESS_TOKEN` environment input and the
  `--require-auth` gate to `./scripts/edge pilot check`.
- Authenticated checks cover identity, system status, onboarding, sites,
  sensors, schedules, findings, and reports.
- The health checker now supports authenticated JSON checks while recording
  only URL, status code, latency, JSON validity, and non-secret error codes.
- Missing credentials fail explicitly when `--require-auth` is supplied and are
  advisory otherwise.
- Updated the pilot acceptance guide and runbook with an environment-only
  token workflow.
- Corrected the roadmap baseline to `v0.3.8` and recorded that implementation
  checkpoints now continue through this checkpoint.

Validation:

- Focused pilot-acceptance and hosted-health tests passed: `9` tests.
- Full local release gate passed at `550df01` with `132` backend/agent tests,
  `32` frontend tests, production build, `28` desktop/mobile browser workflows,
  npm audit, archive checksum, and credential-path checks.
- PR `#44` passed hosted verification and merged to `main` at `b6a89cc`.
- GitHub release workflow `29290748111` passed from tag `v0.3.8` at
  `b6a89cc`, including the exact release gate and package publication.
- Release [`v0.3.8`](https://github.com/Techris93/secopsai-edge/releases/tag/v0.3.8)
  contains the versioned archive, latest archive, checksums, and bootstrap
  installer.

Release workflow correction:

- The prior `v0.3.7` workflow failed only because the release had been created
  manually before the tag workflow reached its publish step. The workflow now
  detects an existing release and refreshes verified assets with `--clobber`,
  while preserving the exact tag/main and release-gate checks. The `v0.3.8`
  workflow exercised this path successfully for a new release.

External boundary:

- This proves the credential can reach the selected authenticated endpoints; it
  does not prove a real scan, notification delivery, seven-day soak, paid
  Render durability, or TL-WN722N hardware behavior.

Next checkpoint:

- Publish the verified release, then collect the remaining external pilot
  evidence gates without treating this preflight as a substitute for them.

## Checkpoint 054 - Hosted Operator Evidence

Status: partial external evidence recorded; pilot acceptance remains pending

Scope:

- Use the released authenticated preflight against the live hosted API and
  record which external acceptance gates are genuinely proven.
- Distinguish a local DNS/network limitation from a failed Cloudflare Pages
  deployment without weakening the acceptance standard.

Evidence:

- Render `/healthz` and `/readyz` returned HTTP `200` for `v0.3.8`; readiness
  reported schema `0016_wifi_provenance`.
- Authenticated identity, system status, onboarding, sites, sensors, schedules,
  findings, and reports all returned HTTP `200` with valid JSON using the
  environment-only pilot credential.
- Public DNS-over-HTTPS returned records for the Pages hostname, but the local
  resolver classified the dashboard check as `dns_resolution_failed` and direct
  HTTPS requests were reset from this workstation. The dashboard gate therefore
  remains unaccepted until an independent browser/network check succeeds.
- Nmap and Python checks passed; worker, Wi-Fi, notification, soak, recovery,
  backup, and hardware exercises were not performed by this non-destructive run.

Authoritative record:

- [pilot-evidence-2026-07-15.md](pilot-evidence-2026-07-15.md)

Next checkpoint:

- Run the remaining pilot acceptance matrix from an independent network and a
  fresh sensor host, then record a signed go/no-go decision.

## Checkpoint 055 - Hosted Core API Activation

Status: implementation and hosted integration proof complete; external pilot
acceptance remains pending

Scope:

- Activate the hosted Core API as the normalized Edge destination.
- Verify the Edge export, Core ingest boundary, and operator workspace end to
  end without retaining raw scanner telemetry in Core.

Completed changes:

- Merged Core hosted sync support to Core `main` through PR `#44` at merge
  commit `bf1e4f8`.
- The hosted Core service is live at
  `https://secopsai-core-api.onrender.com` on a protected Render Starter
  instance with a persistent SQLite disk.
- Created a temporary seven-day `core:export` credential for validation only,
  pushed the current normalized Edge bundle, and revoked the temporary
  credential after verification.
- Hosted Core accepted the bundle with contract
  `secopsai.edge.bundle.v1`: `11` graph nodes, `17` graph edges, and `10`
  findings.
- The authenticated hosted Core workspace now reports `4` assets, `10`
  findings, `1` site, and `1` sensor. The response contained no raw or packet
  telemetry keys.
- The first request returned a transient `502` while the Render service was
  warming; the immediate retry succeeded. Treat the hosted preflight as a
  required retryable operation and investigate any repeated failures through
  Render logs before using the service for customer data.

Validation:

- Core PR `#44` passed Cloudflare Pages, security, SAST, dependency, license,
  and Python 3.10/3.11 checks before merge.
- Core full suite passed: `251` tests, `13` warnings, and `4` subtests.
- Hosted `/healthz`, `/readyz`, authenticated `/api/v1/workspace`, and the
  normalized Edge ingest endpoint returned valid responses.
- Temporary validation credentials were removed; production credentials must
  be created and stored by the operator through the documented Settings/Render
  workflow.

External boundary:

- This proves the current hosted Edge-to-Core transfer path, not a seven-day
  customer soak, paid Render durability/PITR drill, notification delivery,
  second-owner recovery, or independent dashboard browser availability.

Next checkpoint:

- Verify the canonical dashboard's live Core/Edge aggregation from an
  independent browser network, then complete the remaining fresh-host,
  provider, backup, and paid-pilot evidence gates.

## Checkpoint 056 - Hosted Core Cold-Start Recovery

Status: complete; external pilot acceptance remains pending

Scope:

- Make the real sensor-side hosted Core sync resilient to a Render cold start
  or short-lived network interruption.

Completed changes:

- The supervised `core sync-service` runner retries Core import `500`, `502`,
  `503`, and `504` responses plus transient URL/network failures up to three
  times with bounded backoff.
- Authentication failures, redirects, oversized responses, malformed JSON,
  and validation errors still fail immediately and remain non-retryable.
- The direct Core CLI client has the same bounded retry behavior for operators
  using `secopsai edge sync --remote-only`.

Validation:

- Focused Core integration tests passed: `11` tests.
- Sensor hosted sync-service tests passed: `7` tests, including a real local
  HTTP bridge that returns `502` once and then confirms import.
- Edge PR `#48` passed the full release verification and merged to `main` at
  `4f52efc`.

External boundary:

- Retries improve recoverability but do not prove Render durability, a seven-
  day soak, notification delivery, or customer-host installation.

Next checkpoint:

- Complete the independent dashboard availability check and the remaining
  fresh-host, paid-infrastructure, provider, hardware, and recovery evidence.

## Checkpoint 057 - v0.3.9 Release Evidence

Status: released; external pilot acceptance remains pending

Scope:

- Ship the hosted Core recovery fix in the public sensor package and verify the
  release workflow after the earlier duplicate-release incident.

Release evidence:

- Edge `main` contains the retry hardening and version-safe worker heartbeat
  assertion at merge commit `cfddbc7`.
- Tag `v0.3.9` is published from the verified `main` commit.
- GitHub release workflow run `29377706020` passed in `3m11s`, including the
  exact release gate, dependency audit, package build, checksum generation,
  and release publication.
- Release [`v0.3.9`](https://github.com/Techris93/secopsai-edge/releases/tag/v0.3.9)
  contains the versioned archive, versioned checksum, latest archive, latest
  checksum, and bootstrap installer.
- The provenance attestation step is intentionally skipped because this is a
  user-owned private repository; the release still publishes SHA-256 manifests
  from the verified tag workflow.

Correction captured:

- The first `v0.3.9` PR verification failed only because a worker-heartbeat
  test hard-coded `0.3.8`. The test now derives the version from the agent
  package, the corrected verification passed, and no broken tag was published.

External boundary:

- Package publication is verified; a fresh-host install, reboot survival,
  seven-day soak, and customer pilot go/no-go still require an operator test.

Next checkpoint:

- Exercise the `v0.3.9` bootstrap on a clean MacBook or Linux host and record
  installation, service, recovery, and uninstall evidence.

## Checkpoint 058 - Clean-host Bootstrap Evidence

Status: partial; service and long-running pilot acceptance remain pending

Scope:

- Verify that a pilot can obtain the released sensor package and complete
  enrollment without cloning the source repository or exposing credentials in
  command output.

Evidence:

- The public `v0.3.9` bootstrap installer was downloaded from the verified
  GitHub release into an isolated temporary directory.
- Installation completed with a short-lived one-time enrollment token and
  created owner-only sensor credentials.
- The sensor registered successfully, was disabled after validation, and the
  temporary installation directory was removed.
- No service was started, no network scan was run, no raw telemetry was
  collected, and no credential appeared in captured output.

Remaining external boundary:

- This does not prove launchd/systemd startup, reboot survival, upgrade
  rollback, uninstall, or a seven-day worker soak.
- `dashboard.secopsai.dev` is attached to the `secopsai-dashboard` Pages
  project but remains pending until the CNAME record is created and verified.

Next checkpoint:

- Complete the operator-controlled service/reboot/upgrade/uninstall exercise
  and activate the dashboard custom-domain DNS record.

## Checkpoint 059 - macOS Worker Service Path

Status: partial; reboot, upgrade rollback, uninstall, and long-running soak
remain pending

Scope:

- Verify the released sensor package can run as a persistent macOS worker and
  make the source-checkout privacy boundary explicit.

Evidence:

- A direct launchd exercise from this repository under `~/Documents` failed at
  the macOS privacy boundary with `operation not permitted`. No existing
  service was present, and the validation service file/logs were removed after
  the test.
- The helper now rejects macOS worker-service installation from
  `~/Documents`, `~/Desktop`, `~/Downloads`, or iCloud Drive by default and
  prints the released-installer recovery path. An explicit override remains
  available only for an operator who has granted the required macOS access.
- The released `v0.3.9` package was installed in an isolated path outside
  protected folders, configured with owner-only cloud credentials, and started
  through launchd. The worker reached the hosted API and reported its waiting
  state with no queued scan job; it was then stopped and all validation files
  were removed.
- `./scripts/edge worker --cloud --once` also completed an idle hosted poll
  without claiming or running a scan.

Validation:

- Focused worker-service tests passed: `8` tests.
- Full Edge gate passed: `134` backend/agent tests, `32` frontend tests,
  production build, `28` desktop/mobile browser workflows, and `0` npm audit
  vulnerabilities.

Remaining external boundary:

- Reboot survival, upgrade rollback, uninstall, Linux/systemd appliance
  validation, and a seven-day worker soak still require operator evidence.

Next checkpoint:

- Run the released installer on the target host through a reboot and upgrade
  cycle, then record the pilot notification, backup, recovery, and exit gates.

## Checkpoint 060 - Worker Lifecycle Cleanup and Cross-Repo Gate

Status: implementation complete; external pilot acceptance remains pending

Scope:

- Close the worker-service lifecycle gap discovered during the macOS service
  path validation.
- Make uninstall a supported, repeatable operator action and expose it from
  the onboarding command cards.
- Re-run the Edge, Core, canonical dashboard, and OpenClaw verification gates
  before continuing with external acceptance work.

Completed changes:

- Added `./scripts/edge worker uninstall` for macOS launchd and Linux systemd
  user services. It stops the service, removes the user service definition,
  and reloads systemd where applicable.
- Added worker-service coverage proving the uninstall command removes the
  expected service definition on the current platform test path.
- Added an onboarding dashboard command card for copying the worker uninstall
  command, alongside start, status, and logs.
- Updated the README, installation guide, Render/Cloudflare deployment guide,
  and runbook so source-checkout onboarding is foreground-only and released
  installs are the supported path for persistent macOS services.

Validation:

- Edge full gate: `135` backend/agent tests, `33` frontend tests, production
  Next.js build, `28` desktop/mobile Chromium browser workflows, and `0` npm
  audit vulnerabilities.
- Main SecOpsAI Core full suite: `253` tests passed.
- Canonical SecOpsAI dashboard: Node tests and type/check gate passed.
- OpenClaw SecOpsAI plugin: tests and production build passed.
- Hosted Edge/Core health and readiness checks were previously verified; no
  network scan or raw telemetry collection was performed during this gate.

Remaining external boundary:

- Reboot survival, upgrade rollback, uninstall on the target pilot host,
  Linux/systemd appliance validation, and a seven-day worker soak still need
  operator evidence.
- Paid Render API/PostgreSQL activation and PITR restore drill, real SMTP or
  notification-provider delivery, second-owner MFA recovery, manual
  VoiceOver/NVDA review, and dashboard custom-domain DNS activation remain
  external acceptance tasks.

Next checkpoint:

- Complete the target-host lifecycle exercise and record the final controlled
  pilot go/no-go evidence, then move to paid-pilot hardening only for gaps
  revealed by that exercise.

## Checkpoint 061 - v0.3.10 Sensor Package Release

Status: released; external pilot acceptance remains pending

Scope:

- Ship the checkpoint 060 worker lifecycle cleanup in the public sensor
  package rather than leaving it only in the source checkout.
- Verify the release was built from `main`, passed the release gate, and
  contains the new lifecycle command.

Release evidence:

- API, agent, and web package versions were aligned at `0.3.10` in the
  release-preparation commit `855072a`.
- Local `./scripts/release-gate` passed at `855072a`, including `135`
  backend/agent tests, `33` frontend tests, the production build, `28`
  desktop/mobile browser workflows, audit checks, and archive verification.
- PR `#56` passed hosted verification and was merged into `main`.
- Tag `v0.3.10` was created from the verified main ancestry.
- GitHub release workflow `29381687693` passed in `3m15s`. It verified the
  release commit, package archive, SHA-256 manifest, and publication steps.
- Published archive inspection passed: the package checksum was valid, the
  archive contains `worker uninstall`, and the agent reports version
  `0.3.10`.
- Release [`v0.3.10`](https://github.com/Techris93/secopsai-edge/releases/tag/v0.3.10)
  contains the versioned archive, versioned checksum, latest archive, latest
  checksum, and bootstrap installer.

External boundary:

- GitHub artifact provenance attestation remains unavailable for this private
  repository; the release workflow records that limitation and publishes
  SHA-256 manifests from the verified tag.
- A target-host reboot, upgrade rollback, uninstall, Linux/systemd exercise,
  and seven-day worker soak are still required before external pilot go/no-go.

Next checkpoint:

- Run the v0.3.10 installer on the target MacBook or Linux sensor host through
  the lifecycle exercise and record the final acceptance evidence.

## Checkpoint 062 - Sensor-Offline Notification Evaluation

Status: implementation complete; hosted migration verified; external pilot
exercise remains pending

Scope:

- Make sensor health operationally useful without requiring an operator to keep
  the dashboard open.
- Use the existing hosted notification scheduler to detect stale sensors while
  keeping notification volume bounded and recovery explicit.

Completed changes:

- Added migration `0017_sensor_offline_alert` and the nullable
  `sensors.offline_alerted_at` marker. Alembic upgrade and drift checks pass.
- Added a sensor-health helper that marks a previously-seen stale sensor
  offline, creates one minimized `sensor_offline` notification per outage, and
  records an audit event without storing raw scan data in the payload.
- Heartbeats, scan claims, scan starts, failed/completed scan jobs, and scan
  ingestion clear the outage marker so a later outage can alert again.
- Never-seen or disabled sensors do not generate offline alerts.
- The scheduler response exposes `sensor_offline_alerts` for cron evidence and
  operational troubleshooting.
- Updated pilot, deployment, release, and evidence documentation for the
  three-minute staleness threshold and five-minute scheduler cadence.

Validation:

- Focused notification and scan-job tests passed, including first alert,
  duplicate suppression, heartbeat recovery, re-alerting, and never-seen
  sensors.
- Full backend/agent suite passed.
- Dashboard tests: `33` passed; production build passed; `npm audit` found
  `0` vulnerabilities.
- Local PostgreSQL migration `0017_sensor_offline_alert` applied successfully;
  `alembic check` reported no drift.
- Package version was aligned to `0.3.11` for the release gate.

Remaining external boundary:

- A real notification destination, target-host worker outage/recovery, and
  seven-day scheduler/soak exercise still require operator evidence.

Next checkpoint:

- Exercise a real notification destination and target-host worker outage/recovery,
  then record the final controlled-pilot acceptance evidence.

## Checkpoint 066 - Sensor Release Visibility

Status: implementation complete; release and hosted deployment verification
remain pending

Scope:

- Make sensor lifecycle state visible to operators without introducing
  unattended remote code execution or an unreviewed fleet rollout mechanism.
- Reuse the verified GitHub release/bootstrap and rollback path already used by
  the pilot installer.

Completed changes:

- Added semantic version comparison for sensor heartbeats. The API now exposes
  `recommended_version`, `release_status`, and `upgrade_available` on each
  sensor. Invalid or missing versions are reported as `unknown`; disabled
  sensors are reported as `disabled`.
- Added Sites release status text and a `Copy upgrade` action for outdated
  sensors. The copied command supports authenticated GitHub CLI downloads for
  the private repository and a public curl fallback, then invokes the exact
  versioned bootstrap with `--upgrade`.
- Added the read-only `./scripts/edge worker release-check --cloud` command for
  terminal-based release verification. It does not download, install, or
  mutate the sensor.
- Added API, CLI syntax, and dashboard tests for current, outdated, ahead,
  unknown, disabled, and copy-action states.
- Aligned API, agent, and dashboard package versions at `0.3.12` for the
  release gate.

Validation:

- Focused API release-state tests passed.
- Full backend/agent suite, frontend suite, production build, and npm audit
  passed locally before release preparation.
- `bash -n scripts/edge` and the local read-only release-check command passed.

Remaining external boundary:

- The v0.3.12 package must pass the hosted release workflow and be deployed
  before the hosted API can report `recommended_version: 0.3.12`.
- An operator must still perform a target-host upgrade/rollback exercise and
  retain evidence before calling the lifecycle path pilot-ready.

Next checkpoint:

- Run the v0.3.12 release gate, merge the release branch, verify hosted
  deployment identity, and exercise one operator-controlled upgrade check.

## Checkpoint 067 - v0.3.12 Hosted Release Evidence

Status: released; target-host lifecycle exercise remains pending

Scope:

- Close the release and hosted-deployment evidence for checkpoint 066.
- Keep the historical GitHub release publication failure accurately
  distinguished from the current successful release path.

Release evidence:

- PR `#63` passed hosted verification and was merged into `main`.
- Tag `v0.3.12` was created from verified main ancestry.
- GitHub release workflow `29385802680` passed in `3m41s`, including exact
  release-commit verification, the full release gate, package archive and
  checksum verification, browser workflows, npm audit, and publication.
- The private-repository provenance limitation was recorded by the workflow;
  SHA-256 manifests remain the available package-integrity evidence.
- The downloaded v0.3.12 archive checksum passed and archive inspection found
  `scripts/edge` while excluding credential and build paths.
- Render `/healthz` returned version `0.3.12`, commit `91db49c7b9dd`; Render
  `/readyz` returned schema `0017_sensor_offline_alert` and version `0.3.12`.

Historical failure clarification:

- The old v0.3.6 and v0.3.7 release runs failed only at publication because
  the tag already had a GitHub release. The release workflow now detects an
  existing release and refreshes assets with `gh release upload --clobber`.
- A fresh v0.3.12 run exercised that corrected path successfully.

Remaining external boundary:

- An operator must still perform an upgrade/rollback exercise on the target
  sensor host and retain the evidence before calling the lifecycle path
  pilot-ready.

Next checkpoint:

- Complete the target-host lifecycle and controlled-pilot acceptance gates.

## Checkpoint 068 - Sensor-Scoped Release Status

Status: released; hosted evidence closed; target-host exercise remains pending

Scope:

- Remove the administrator-token requirement from the sensor host's cloud
  release check.
- Give trusted local automation a narrow, read-only sensor lifecycle surface.

Completed changes:

- Added `GET /api/v1/sensors/{sensor_id}/release-status`, authenticated only
  with that sensor's `X-Sensor-Token`. It returns the sensor's own version,
  recommended API release, and release status without exposing other sensors.
- Updated `./scripts/edge worker release-check --cloud` to use the saved
  `.cloud-sensor.env` credential and the scoped endpoint. It no longer prompts
  for or reads a workspace administrator token.
- Added API coverage proving an authenticated sensor token can read its own
  release state.
- Aligned API, agent, and dashboard package versions at `0.3.13` for the
  release gate.

Validation:

- Focused scan-job/release tests passed.
- `bash -n scripts/edge`, `git diff --check`, and the local read-only release
  check passed.

Remaining external boundary:

- An operator must still perform an upgrade/rollback exercise on the target
  sensor host and retain evidence before calling the lifecycle path
  pilot-ready.

Next checkpoint:

- Complete the target-host lifecycle and controlled-pilot acceptance gates.

## Checkpoint 069 - OpenClaw Release Check Integration

Status: released; local plugin verification passed

Scope:

- Expose the sensor-scoped release check through the OpenClaw automation
  bridge without adding an unapproved upgrade action.

Completed changes:

- OpenClaw plugin PR `#7` added the read-only
  `secopsai_edge_release_check` tool. It invokes
  `worker release-check --cloud` through the canonical Edge helper.
- Plugin documentation and its allow-list example now include the tool.
- Plugin tests verify the structured argument list and safe output path.

Validation:

- OpenClaw `npm test` passed: TypeScript build and 2 tests.
- Edge v0.3.13 release workflow and Render health/readiness evidence passed.

Remaining external boundary:

- Install/reload the released plugin in the operator's OpenClaw runtime and
  exercise the tool with a real sensor credential environment.

Next checkpoint:

- Complete the target-host lifecycle, OpenClaw runtime exercise, and remaining
  controlled-pilot acceptance gates.

## Checkpoint 070 - v0.3.14 Release-Check Repair

Status: released; target-host lifecycle exercise remains pending

Scope:

- Repair the hosted worker release-check command discovered during a real
  cloud exercise.
- Publish the corrected formatter in the sensor package rather than leaving
  the fix only on `main`.

Completed changes:

- PR `#67` replaced the conflicting shell/Python f-string quote boundary with
  safe `.format()` rendering and added a regression test for a valid hosted
  release-status response.
- PR `#68` aligned the API, agent, and dashboard package versions at `0.3.14`.
- Tag `v0.3.14` was created from verified `main`. Release workflow
  `29387904397` passed in `3m13s`, including the full release gate, package
  build, checksum publication, and GitHub release publication.
- Render `/healthz` returned version `0.3.14`, commit `68f58d7dcbb1`;
  `/readyz` returned version `0.3.14` and schema
  `0017_sensor_offline_alert`.
- The downloaded v0.3.14 archive checksum passed and archive inspection
  confirmed the corrected packaged `scripts/edge`.
- A live `./scripts/edge worker release-check --cloud` completed successfully
  and reported the enrolled sensor as `v0.3.9` versus recommended `v0.3.14`,
  status `outdated`. The command is read-only.

Validation:

- Edge focused release/worker tests passed.
- Edge PR #67 CI passed all 28 checks.
- Edge PR #68 CI passed all 28 checks.
- The v0.3.14 release workflow passed all release steps.
- Core full suite passed: 253 tests.
- Canonical dashboard tests/checks passed.
- OpenClaw plugin tests passed.

Remaining external boundary:

- Install v0.3.14 on the target sensor host, exercise upgrade/rollback,
  reboot survival, uninstall, and long-running soak.
- Install/reload the merged OpenClaw plugin in the real runtime and exercise
  `secopsai_edge_release_check`.

Next checkpoint:

- Complete the target-host lifecycle and controlled-pilot acceptance gates.

## Checkpoint 071 - v0.3.14 Clean-Host Lifecycle Evidence

Status: partial external evidence recorded; reboot and long-running soak remain pending

Scope:

- Exercise the released MacBook installation workflow as a real hosted sensor.
- Verify the service lifecycle and rollback behavior without running a network
  scan.

Completed changes and evidence:

- Created a temporary 30-minute site-scoped enrollment through the hosted API.
- Downloaded and checksum-verified the private `v0.3.14` release through the
  documented authenticated GitHub CLI path.
- Installed the package under
  `~/.local/share/secopsai-edge-lifecycle-validation`, outside macOS protected
  folders, and started the launchd worker.
- After the first heartbeat, the temporary sensor reported worker
  `v0.3.14`, recommended release `v0.3.14`, status `current`. The worker stayed
  in the expected waiting state and its error log was empty.
- Stopped and restarted the service successfully.
- Ran an intentionally invalid `--upgrade` enrollment. It failed with exit
  code `56`, restored the previous `v0.3.14` installation, and left no
  `.previous` directory behind.
- Rechecked the heartbeat after restart and received `release_status=current`.
- Uninstalled the worker, disabled the temporary hosted sensor, and removed
  only the isolated validation runtime and logs.

Validation:

- Released bootstrap and dependency installation passed.
- launchd install/start/stop/status/uninstall passed.
- Heartbeat and sensor-scoped release check passed.
- Upgrade failure rollback and credential-preservation path passed.
- No network scan or raw telemetry collection was performed.

Remaining external boundary:

- Reboot survival must be tested on the intended target host.
- A seven-day worker soak, scheduled scan, real notification delivery and
  offline/recovery alert, paid Render/PITR drill, second-owner MFA recovery,
  and TL-WN722N Linux/Raspberry Pi validation remain pending.
- The merged OpenClaw plugin still needs installation/reload and a real
  `secopsai_edge_release_check` runtime exercise.

Next checkpoint:

- Complete reboot/soak and notification acceptance, then close the remaining
  hosted pilot go/no-go gates.

## Checkpoint 072 - Deployed Dashboard Health Endpoint Correction

Status: merged; dashboard DNS acceptance remains external

Scope:

- Align all hosted health and pilot acceptance checks with the actual
  Cloudflare Pages project.
- Preserve evidence that distinguishes a correct endpoint from a local DNS
  failure.

Completed changes:

- PR `#71` changed the hosted health workflow, `./scripts/edge cloud
  uptime-check`, and `./scripts/edge pilot check --cloud` defaults from the
  retired `secopsai-edge.pages.dev` hostname to the documented
  `secopsai-dashboard.pages.dev` project.
- Centralized the default dashboard URL in
  `scripts/hosted_health_check.py` and added a regression test to prevent the
  old hostname from returning.
- The corrected hosted acceptance run confirmed Edge API liveness and
  readiness at v0.3.14 with schema `0017_sensor_offline_alert`.
- The dashboard probe failed only because this workstation could not resolve
  the Pages hostname. No response bodies, tokens, scans, or telemetry were
  collected.

Validation:

- Focused hosted-health and pilot-acceptance tests passed: 10 tests.
- Shell syntax and Python compilation checks passed.
- PR `#71` full GitHub verification passed in `3m35s` and was merged.

Remaining external boundary:

- Re-run the dashboard probe from a network with working Pages DNS after the
  project hostname and `dashboard.secopsai.dev` CNAME are active.
- Reboot survival, seven-day soak, scheduled scan, real notification delivery
  and offline/recovery alert, paid Render/PITR, second-owner MFA recovery,
  and TL-WN722N Linux/Raspberry Pi validation remain pending.

Next checkpoint:

- Close the dashboard DNS/account/notification gates where operator access is
  available, then record the final pilot go/no-go decision.

## Checkpoint 073 - OpenClaw Current-Runtime Plugin Evidence

Status: plugin runtime integration closed; model tool-policy exercise remains external

Scope:

- Make the merged OpenClaw SecOpsAI plugin load on the current local gateway.
- Verify that the Edge operator tools are present without invoking scans or
  state-changing actions.

Completed changes and evidence:

- OpenClaw plugin PR `#8` updated the compatibility range from the legacy
  `pluginApi: "1"` declaration to `>=2026.6.10`.
- OpenClaw plugin PR `#9` declared all 27 registered tools in
  `openclaw.plugin.json` under `contracts.tools` and added a manifest-to-code
  regression test.
- The local plugin installed successfully through
  `openclaw plugins install -l`, the gateway restarted, and runtime inspection
  reported plugin version `1.0.2` as loaded and activated with all 27 tools and
  zero diagnostics.
- The plugin configuration now points to the real Core and Edge paths. The
  gateway remains loopback-only.

Validation:

- Plugin test suite passed: 4 tests.
- Runtime plugin inspection passed with 27 tool names and no diagnostics.
- No network scan, scan queue, report generation, worker start/stop, or raw
  telemetry operation was invoked.

Remaining external boundary:

- A live model-driven OpenClaw turn was run with the approved Google provider.
  The model completed normally, but the agent's `coding` tool profile removed
  the SecOpsAI plugin tools before dispatch, so it reported
  `secopsai_edge_worker_status` as unavailable instead of invoking it. The
  direct plugin runtime call is healthy; the remaining work is to configure
  the operator's OpenClaw agent policy so the exact plugin tool is visible in
  model turns, without changing global plugin trust or unrelated plugins.
- The unrelated OpenClaw warning about conflicting Brave plugin install
  metadata remains outside the SecOpsAI plugin.

Next checkpoint:

- Exercise one read-only plugin tool through an OpenClaw agent with an
  explicitly compatible tool policy, then close the remaining notification,
  account, DNS, paid-infrastructure, reboot/soak, and hardware acceptance
  gates.
