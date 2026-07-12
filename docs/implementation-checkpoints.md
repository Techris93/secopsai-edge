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

Known risks:

- Main SecOpsAI remains a dirty worktree and was intentionally not changed in
  this checkpoint.
- The dashboard still needs stronger empty/error panels for blocked API state;
  this checkpoint fixed truthfulness before redesigning every state surface.
- Existing FastAPI startup event deprecation warnings remain and should be
  handled in a later backend hygiene pass.

Do not touch yet:

- Main SecOpsAI dirty worktree at `/Users/chrixchange/secopsai`.
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

Core worktree note:

- `/Users/chrixchange/secopsai` contains unrelated generated blog/news changes
  that are not part of this checkpoint.
- This checkpoint should only modify or validate Edge/Core integration files
  unless a defect blocks the sync path.

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

## Completion Rules

A checkpoint is complete only when:

- Code or docs changed in the checkpoint are listed here.
- Tests or validation commands are recorded.
- Known risks and next tasks are updated.
- The repo status is checked and summarized.
