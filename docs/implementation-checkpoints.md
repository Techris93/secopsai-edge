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

## Completion Rules

A checkpoint is complete only when:

- Code or docs changed in the checkpoint are listed here.
- Tests or validation commands are recorded.
- Known risks and next tasks are updated.
- The repo status is checked and summarized.
