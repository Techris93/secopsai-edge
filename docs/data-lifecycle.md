# Data Lifecycle And Pilot Exit

SecOpsAI Edge keeps current inventory and findings useful while aging out
operational history according to a workspace policy. The default policy keeps:

| Data | Default |
| --- | ---: |
| Normalized asset observations | 90 days |
| Completed scan jobs and runs | 180 days |
| Completed notification deliveries | 90 days |
| Expired invitation and reset records | 30 days |
| Expired enrollment and integration records | 90 days |
| Reports | 365 days |
| Audit logs | 365 days |

Settings > Data Lifecycle lets an administrator change these bounded values and
run cleanup immediately. The five-minute scheduler checks retention on every
cycle but each workspace is processed at most once per 24 hours unless an
operator deliberately selects **Run cleanup**.

Cleanup never removes current assets, services, Wi-Fi networks, open findings,
active schedules, active jobs, users, organizations, or live credentials.

## Customer Export

Sites > Export downloads `secopsai.edge.site-export.v1` JSON. It includes the
selected site's normalized sensors, scans, schedules, assets, observations,
services, Wi-Fi networks, baselines, findings, notes, reports, and site-scoped
notification configuration.

The export excludes:

- raw observation payloads and raw Nmap output;
- sensor and enrollment token hashes;
- user passwords, sessions, MFA secrets, and recovery codes;
- integration credentials;
- notification destinations and webhook URLs.

Export is workspace scoped and audit logged. Treat the downloaded file as
sensitive customer data because it contains IP addresses, hostnames, MAC/BSSID
identifiers, findings, and report content.

## Site Deletion

Sites > Delete is an owner-only destructive workflow. It requires:

1. no queued, claimed, or running scan job for the site;
2. the exact site name;
3. an explicit permanent-deletion acknowledgement;
4. the owner's current password;
5. a current TOTP or one-use recovery code when MFA is enabled.

Deletion removes the site and its sensors, enrollments, assets, normalized
observations, services, Wi-Fi inventory, baselines, findings and notes, reports,
scan jobs/runs/schedules, site notification endpoints/deliveries, and linked
audit records. A final organization audit record stores only the removed row
counts and site identifier, not the site name or telemetry.

Always export the site and create a verified database backup before deletion.
Recovery requires restoring that separate backup; the product has no undelete
button.

## Pilot Exit Checklist

1. Disable schedules and the sensor.
2. Export the site from Sites.
3. Download the final PDF report if required.
4. Create and verify a database backup under the agreed retention terms.
5. Delete the site using an owner account and MFA.
6. Uninstall the worker from the customer sensor.
7. Verify Sites, Assets, Findings, and Reports no longer expose the site.
8. Record the `site.deleted` audit event and the agreed backup destruction date.
