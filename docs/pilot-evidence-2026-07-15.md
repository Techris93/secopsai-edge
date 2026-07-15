# Pilot Evidence - 2026-07-15

This record captures the non-destructive hosted checks performed through the
`v0.3.14` release. Earlier sections retain the historical v0.3.9 through
v0.3.12 validation
where that package was exercised. It contains no bearer tokens, response
bodies, scan output, or customer telemetry.

## Passed

- Edge release `v0.3.9` is published from the verified GitHub workflow.
- Render API `/healthz` returned HTTP `200`, status `ok`, version `0.3.9`.
- Render API `/readyz` returned HTTP `200`, status `ready`, version `0.3.9`,
  schema `0016_wifi_provenance`.
- Authenticated operator preflight returned HTTP `200` and valid JSON for:
  identity, system status, onboarding, sites, sensors, schedules, findings,
  and reports.
- Local Nmap and Python dependency checks passed.

## Latest hosted deployment

- Render Edge `/healthz` returned HTTP `200`, status `ok`, version `0.3.14`,
  commit `68f58d7dcbb1`.
- Render Edge `/readyz` returned HTTP `200`, status `ready`, version `0.3.14`,
  schema `0017_sensor_offline_alert`.
- Render Core `/readyz` returned HTTP `200`, status `ready`, using its hosted
  SQLite data store.
- The v0.3.14 deployment is the current hosted release; the earlier v0.3.9
  through v0.3.12 bullets above remain historical evidence.

## v0.3.14 hosted acceptance probe correction

- The hosted health monitor and pilot acceptance defaults now target the
  documented Cloudflare Pages project, `secopsai-dashboard.pages.dev`, rather
  than the retired `secopsai-edge.pages.dev` hostname.
- The corrected acceptance probe confirmed Edge API liveness and readiness at
  v0.3.14 with schema `0017_sensor_offline_alert`.
- The dashboard probe still failed from this workstation with a DNS resolution
  error. This is an external Pages/DNS gate, not an API or release failure;
  re-run the probe from a network that can resolve Pages after the project
  hostname and `dashboard.secopsai.dev` CNAME are active.
- PR `#71` merged the URL correction after the full GitHub verification job
  passed in `3m35s`.

## OpenClaw current-runtime integration

- OpenClaw plugin PR `#8` aligned the SecOpsAI plugin with the current
  `2026.6.10` plugin API range, and PR `#9` declared its 27 registered tools
  in the manifest contract.
- Local installation and gateway restart succeeded. Runtime inspection
  reported plugin version `1.0.2` as loaded and activated with 27 tools and
  zero diagnostics.
- The merged plugin was also exercised directly with the real Core and Edge
  paths. It registered all 27 tools and the read-only
  `secopsai_edge_worker_status` action returned the expected no-service state
  without an error, scan, or mutation.
- No scan, queued job, report, worker mutation, or raw telemetry operation was
  invoked during this check.
- An initial live model-driven read-only turn exposed an embedded-agent path
  boundary: the model could see the plugin contract but the plugin received
  no configured repository path and fell back to `~/secopsai-edge`. This was
  corrected in plugin PR `#10`; it was not a plugin load or tool-policy
  failure.
- Plugin PR `#10` added `SECOPSAI_CORE_PATH` and `SECOPSAI_EDGE_PATH` fallback
  configuration for embedded/local agent runs while preserving explicit
  plugin configuration precedence. After the fix, a fresh live Google model
  turn invoked `secopsai_edge_worker_status` against the real Edge checkout
  and returned the expected stopped-worker state. No scan or mutation ran.

## Cross-repository verification after checkpoint 073

The following suites were rerun from the clean repositories after the
OpenClaw runtime and roadmap corrections:

- Edge: `144` backend/agent tests, `34` frontend tests, `28` desktop/mobile
  browser workflows, production Next.js build, and `npm audit` with zero
  vulnerabilities.
- Core: `253` tests, `13` warnings, and `4` subtests passed.
- Canonical dashboard: `42` Python tests and `13` subtests passed; JavaScript
  tests and syntax checks passed.
- OpenClaw SecOpsAI plugin: `5` tests passed, including compatibility,
  manifest tool-contract, and embedded-agent path fallback checks.

These are local repository verification results. They do not replace the
external notification, DNS, paid-infrastructure, account-recovery,
reboot/soak, or hardware acceptance rows below.

## Hosted infrastructure recheck

- `./scripts/edge status --cloud` returned a running Edge API with readiness
  `ready`.
- `./scripts/edge cloud uptime-check` returned Edge API `/healthz` and
  `/readyz` as healthy on v0.3.14 with schema `0017_sensor_offline_alert`.
- The same health check returned the documented non-secret
  `dns_resolution_failed` result for `secopsai-dashboard.pages.dev`.
- `./scripts/edge cloud drift-check` reported zero drift issues. It warned
  that the current free Render database expires on 2026-07-20; paid
  infrastructure activation and a PITR drill remain mandatory before a real
  external pilot.

## v0.3.14 release-check repair and package evidence

- Edge PR `#67` fixed the hosted worker release-check formatter. The previous
  implementation reached the API but failed while formatting valid JSON because
  shell and Python quote delimiters conflicted.
- The fix is covered by a regression test using a hosted
  `release-status` response. PR `#67` passed the complete Edge CI gate with
  28 checks and was merged into `main`.
- Edge PR `#68` aligned API, agent, and dashboard versions at `0.3.14`. Its
  complete CI gate passed with 28 checks before merge.
- The v0.3.14 release workflow `29387904397` passed in `3m13s`, including the
  full release gate, package build, SHA-256 manifest publication, and GitHub
  release creation.
- The downloaded `secopsai-edge-0.3.14.tar.gz` checksum passed and the
  packaged `scripts/edge` contains the corrected formatter.
- `./scripts/edge worker release-check --cloud` now completes successfully
  against the hosted API and reports the enrolled sensor's actual state:
  the current sensor reported `v0.3.9`, while the hosted recommendation was
  `v0.3.14`, with status `outdated`.
- This does not perform an upgrade. The target-host upgrade, rollback, reboot,
  and soak exercise remain operator acceptance tasks.

## v0.3.14 clean-host lifecycle evidence

- A temporary 30-minute site-scoped enrollment created through the hosted API
  enrolled `v0.3.14` without exposing the administrator token to the installer.
- The released bootstrap downloaded and checksum-verified the private package,
  installed it under an isolated path outside protected folders, installed the
  macOS launchd service, and started it without running a scan.
- After the first heartbeat, the validation sensor reported worker `v0.3.14`,
  recommended release `v0.3.14`, and release status `current`. Worker logs
  reported the expected waiting state with no error output.
- `worker stop` and `worker start` both completed successfully. A deliberately
  invalid upgrade enrollment failed with exit code `56`; the bootstrap restored
  the previous installation and preserved version `0.3.14`. After restart, the
  worker again heartbeated as `current`.
- `worker uninstall` removed the launchd definition. The temporary sensor was
  disabled and the isolated runtime and logs were removed.
- No network scan, packet capture, raw telemetry collection, or customer data
  change was performed during this lifecycle exercise.

## v0.3.13 package and scoped release-status evidence

- The v0.3.13 release workflow `29386712345` passed in `3m16s` after
  verifying main ancestry, the full release gate, archive, checksums, and
  publication.
- The downloaded `secopsai-edge-0.3.13.tar.gz` checksum passed and archive
  inspection found `scripts/edge` while excluding credential and build paths.
- The release is available at
  https://github.com/Techris93/secopsai-edge/releases/tag/v0.3.13.
- Render deployed the same main commit and reports matching version `0.3.13`
  with schema `0017_sensor_offline_alert`.
- `GET /api/v1/sensors/{sensor_id}/release-status` is sensor-token scoped and
  returns only that sensor's release state. The released worker check no longer
  requires a workspace administrator token.
- OpenClaw plugin PR `#7` merged the read-only `secopsai_edge_release_check`
  action, which invokes the same scoped worker command and never upgrades or
  mutates the sensor.

## v0.3.12 package and release evidence

- The v0.3.12 release workflow `29385802680` passed in `3m41s` after verifying
  the tag's main ancestry, release gate, archive, checksums, and publication.
- The release publication step completed successfully with the existing-release
  safe workflow path. The private-repository provenance limitation was recorded
  as a notice; SHA-256 manifests remain the published integrity evidence.
- The downloaded `secopsai-edge-0.3.12.tar.gz` checksum passed and archive
  inspection found `scripts/edge` while excluding credential and build paths.
- The release is available at
  https://github.com/Techris93/secopsai-edge/releases/tag/v0.3.12.
- Render deployed the same main commit and reports the matching `0.3.12`
  version and `0017_sensor_offline_alert` schema.

## v0.3.12 sensor release visibility evidence

- API, agent, and dashboard package versions are aligned at `0.3.12`.
- Sites now reports `current`, `outdated`, `ahead`, `unknown`, or `disabled`
  release state from the worker heartbeat and exposes a copyable, explicit
  upgrade command for outdated sensors.
- `./scripts/edge worker release-check --cloud` is read-only and does not
  download, install, or mutate the sensor.
- The target-host upgrade and rollback exercise remains an operator acceptance
  task; unattended fleet rollout is intentionally not enabled.

## v0.3.11 implementation evidence

- Migration `0017_sensor_offline_alert` adds durable outage-alert deduplication
  without storing raw scan telemetry.
- The notification scheduler marks stale, previously-seen sensors offline and
  emits one `sensor_offline` event per outage. Heartbeat and scan activity clear
  the marker so a later outage can alert again.
- Focused notification and scan-job tests passed for first alert, duplicate
  suppression, heartbeat recovery, re-alerting, and never-seen sensors.
- Hosted deployment and Render `/readyz` evidence are now closed for the
  v0.3.11 migration. Real notification delivery and outage/recovery exercise
  remain operator acceptance tasks.

## Still Pending

- Cloudflare Pages dashboard acceptance is not closed from this workstation.
  The dashboard Pages project is `secopsai-dashboard.pages.dev`; the intended
  custom domain `dashboard.secopsai.dev` is attached to that project but is
  still pending because its CNAME record has not been created. Cloudflare's
  Pages API reports domain status `pending`; independent DNS-over-HTTPS lookup
  returns the Pages project records but returns NXDOMAIN for
  `dashboard.secopsai.dev`. Add the CNAME record, then rerun the independent
  browser/network check. An authenticated attempt to create the record
  through the current Wrangler OAuth token was rejected with Cloudflare API
  error `10000` (DNS-write permission is not present); no DNS state changed.
- Reboot survival and the seven-day sensor soak, scheduled scan, notification delivery, offline
  sensor alert, paid Render/PITR drill, second-owner MFA recovery, and
  TL-WN722N Linux/Raspberry Pi validation remain unperformed.
- Wi-Fi was not treated as a required check and no supported adapter capability
  was available on this MacBook run.

## Clean-host bootstrap evidence

- The public `v0.3.9` bootstrap installer was downloaded from the verified
  GitHub release into an isolated temporary directory.
- Installation completed successfully with a short-lived one-time enrollment
  token and created owner-only sensor credentials.
- The sensor registered successfully, was disabled after validation, and the
  temporary installation directory was removed.
- No service was started, no network scan was run, no raw telemetry was
  collected, and no credential appeared in captured output.
- Launchd/systemd startup, reboot survival, upgrade rollback, and long-running
  soak remain separate operator acceptance steps.

## macOS worker-service validation

- Installing a launchd worker directly from the source checkout under
  `~/Documents` failed with macOS `operation not permitted`; this is the
  expected privacy boundary for that path, not a package failure.
- The released `v0.3.9` package was installed in an isolated path outside
  protected folders, started through launchd, reached the hosted Edge API, and
  reported its waiting state without claiming or running a scan.
- The validation worker was stopped and its temporary service file, logs, and
  installation directory were removed.
- The helper now rejects the protected source-tree service path with a direct
  release-installer instruction.

## Worker lifecycle command

- `./scripts/edge worker uninstall` now stops and removes the user service
  definition on macOS and Linux, so operators do not need to edit launchd or
  systemd files manually.
- The onboarding page exposes the uninstall command as a copyable action.
- The lifecycle helper and dashboard command-card tests passed as part of the
  full Edge gate.

## v0.3.10 package closeout

- The v0.3.10 release workflow `29381687693` passed after verifying the tag's
  main ancestry, release gate, archive, checksums, and publication.
- The downloaded v0.3.10 archive checksum passed and archive inspection found
  the worker uninstall command and agent version `0.3.10`.
- The release is available at
  https://github.com/Techris93/secopsai-edge/releases/tag/v0.3.10.

## v0.3.11 package closeout

- The v0.3.11 release workflow `29383682759` passed in `3m27s` after verifying
  the tag's main ancestry, release gate, archive, checksums, and publication.
- The downloaded v0.3.11 archive checksum passed and archive inspection found
  the sensor-health implementation while excluding credential and build paths.
- The release is available at
  https://github.com/Techris93/secopsai-edge/releases/tag/v0.3.11.

## Reproduction

Run the hosted checks from a network with working DNS and an approved operator
credential held only in the environment:

```bash
export SECOPSAI_PILOT_ACCESS_TOKEN='use-a-short-lived-approved-credential'
./scripts/edge pilot check --cloud --skip-worker --skip-wifi --require-auth \
  --output pilot-authenticated.json
unset SECOPSAI_PILOT_ACCESS_TOKEN
```

Do not commit the generated JSON evidence file. Review it for local paths and
network identifiers before sharing it.
