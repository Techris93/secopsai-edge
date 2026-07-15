# Pilot Evidence - 2026-07-15

This record captures the non-destructive hosted checks performed through the
`v0.3.11` release. Earlier sections retain the historical v0.3.9 and v0.3.10 validation
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

- Render Edge `/healthz` returned HTTP `200`, status `ok`, version `0.3.11`,
  commit `5b1496f0767f`.
- Render Edge `/readyz` returned HTTP `200`, status `ready`, version `0.3.11`,
  schema `0017_sensor_offline_alert`.
- Render Core `/readyz` returned HTTP `200`, status `ready`, using its hosted
  SQLite data store.
- The v0.3.11 deployment is the current hosted release; the earlier v0.3.9
  and v0.3.10 bullets above remain historical evidence.

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
  still pending because its CNAME record has not been created. An independent
  browser/network check is still required after DNS activation.
- The seven-day sensor soak, scheduled scan, notification delivery, offline
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
