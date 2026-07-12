# Demo Script

## 1. Show Onboarding

Open the dashboard and go to Onboarding. Confirm:

- API connected
- site created
- sensor registered
- worker online

If the worker is offline:

```bash
./scripts/edge worker status
./scripts/edge worker start
```

## 2. Queue A Scan

On Overview, enter an authorized CIDR such as:

```text
192.168.1.0/24
```

Click Queue Remote Scan. The local worker claims the job, runs the scan locally, and submits normalized results to the API.

## 3. Review Changes

Open Assets and filter by vendor, type, OS, status, or service. Open Findings and filter by severity, status, and site.

## 4. Triage A Finding

Open a finding detail page. Add a note, acknowledge it, and queue Verify Fixed if it affects an asset.

## 5. Generate A Report

Open Reports, choose a site, and generate a report. Open the report detail page, then:

- Copy Summary
- Copy Brief
- Download Report
- Print

## 6. Show Core Integration

Open Settings and use the SecOpsAI Core Integration buttons:

```bash
./scripts/edge core sync --cloud --core-root /Users/chrixchange/secopsai --output edge-bundle.json
```

Confirm:

```bash
.venv/bin/python -m secopsai.cli graph assets
.venv/bin/python -m secopsai.cli triage list --source secopsai_edge
```
