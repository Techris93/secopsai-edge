# Pilot Evidence - 2026-07-15

This record captures the non-destructive hosted checks performed after the
`v0.3.9` release. It contains no bearer tokens, response bodies, scan output,
or customer telemetry.

## Passed

- Edge release `v0.3.9` is published from the verified GitHub workflow.
- Render API `/healthz` returned HTTP `200`, status `ok`, version `0.3.9`.
- Render API `/readyz` returned HTTP `200`, status `ready`, version `0.3.9`,
  schema `0016_wifi_provenance`.
- Authenticated operator preflight returned HTTP `200` and valid JSON for:
  identity, system status, onboarding, sites, sensors, schedules, findings,
  and reports.
- Local Nmap and Python dependency checks passed.

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
