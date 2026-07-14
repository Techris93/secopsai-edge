# Pilot Evidence - 2026-07-15

This record captures the non-destructive hosted checks performed after the
`v0.3.8` release. It contains no bearer tokens, response bodies, scan output,
or customer telemetry.

## Passed

- Edge release `v0.3.8` is published from the verified GitHub workflow.
- Render API `/healthz` returned HTTP `200`, status `ok`, version `0.3.8`.
- Render API `/readyz` returned HTTP `200`, status `ready`, version `0.3.8`,
  schema `0016_wifi_provenance`.
- Authenticated operator preflight returned HTTP `200` and valid JSON for:
  identity, system status, onboarding, sites, sensors, schedules, findings,
  and reports.
- Local Nmap and Python dependency checks passed.

## Still Pending

- Cloudflare Pages dashboard acceptance is not closed from this workstation.
  The normal resolver classified `https://secopsai-edge.pages.dev` as
  `dns_resolution_failed`. Cloudflare DNS-over-HTTPS returned public A records,
  but direct HTTPS requests from this environment were reset, so an independent
  browser/network check is still required.
- The seven-day sensor soak, scheduled scan, notification delivery, offline
  sensor alert, paid Render/PITR drill, second-owner MFA recovery, and
  TL-WN722N Linux/Raspberry Pi validation remain unperformed.
- Wi-Fi was not treated as a required check and no supported adapter capability
  was available on this MacBook run.

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
