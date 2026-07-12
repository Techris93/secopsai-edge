# Render + Cloudflare Pages Deployment

This deployment keeps LAN scanning local and hosts only the cloud-facing pieces.

## Architecture

- Local MacBook/Raspberry Pi: runs `secopsai-agent` and submits normalized scan payloads.
- Render: hosts FastAPI and managed PostgreSQL.
- Cloudflare Pages: hosts the static dashboard from `web/out`.

## Prerequisites

- Push this project to GitHub, GitLab, or Bitbucket.
- Create a Render account.
- Create a Cloudflare account.
- Keep `SECOPSAI_ADMIN_TOKEN` and sensor tokens private.

## Render API + Postgres

The repository includes `render.yaml`.

1. Commit and push `render.yaml`, `runtime.txt`, and `scripts/render-start-api`.
2. In Render, create a new Blueprint from your Git repository.
3. Fill these prompted values:
   - `SECOPSAI_ADMIN_TOKEN`: a long random automation/recovery token.
   - `SECOPSAI_DASHBOARD_ADMIN_EMAIL`: the first dashboard admin user email.
   - `SECOPSAI_DASHBOARD_ADMIN_PASSWORD`: a long random first dashboard admin password.
   - `SECOPSAI_LOGIN_MAX_ATTEMPTS`: failed attempts before temporary lockout; default `5`.
   - `SECOPSAI_LOGIN_LOCKOUT_SECONDS`: lockout duration; default `900` seconds.
   - `SECOPSAI_CORS_ORIGINS`: your Cloudflare Pages URL, plus local dev if needed.
   - `AI_API_KEY`: optional; add an OpenAI API key to enable live reports.
4. Apply the Blueprint.
5. Confirm the health check:

   ```bash
   curl https://<your-render-api>.onrender.com/healthz
   ```

Expected response:

```json
{"status":"ok"}
```

The Render start script runs Alembic migrations before starting Uvicorn.

### Dashboard Login

For hosted pilots, use the dashboard user login in Settings > API Connection. The admin token flow
still exists for scripts, Render cron, Core sync automation, and emergency recovery, but it should
not be the normal browser login method.

### Live OpenAI Reports

In the Render service environment, set these server-side values:

```text
AI_PROVIDER=openai
AI_API_KEY=<your OpenAI API key>
AI_MODEL=gpt-5.4-mini
```

Redeploy the API, then generate a new report. Existing reports remain unchanged. Never put the API key in a `NEXT_PUBLIC_*` variable or the Cloudflare Pages environment.

## Cloudflare Pages Dashboard

Create a Pages project from the same Git repository.

Use these settings:

- Root directory: `web`
- Build command: `npm ci && npm run build`
- Build output directory: `out`
- Environment variable:
  - `NEXT_PUBLIC_API_BASE_URL=https://<your-render-api>.onrender.com`
  - `NEXT_PUBLIC_SECOPSAI_DEMO_MODE=false` or leave unset for real pilots.

The dashboard is a static Next.js export. It does not include `NEXT_PUBLIC_ADMIN_TOKEN`.
Optional `NEXT_PUBLIC_EDGE_ROOT` and `NEXT_PUBLIC_CORE_ROOT` values control the generic defaults shown in copyable local commands. Operators can override both paths in Settings, where they are stored only in browser local storage.
Open Settings in the dashboard and use the API Connection panel to create a browser session with
your dashboard admin email and password.

For customer pilots, the dashboard should show `API not connected` until the browser session is
created, then `Live API data` after the API is reachable. `Demo data only` should be used only for
sales screenshots or local design review, never to represent real telemetry.

## Local Agent Against Cloud

Configure the hosted API URL:

```bash
./scripts/edge cloud configure https://<your-render-api>.onrender.com
```

Register the local sensor against the hosted API:

```bash
./scripts/edge cloud register
```

Run a scan and submit it to Render:

```bash
./scripts/edge scan 192.168.1.0/24 --cloud
```

Or run the local worker so dashboard-queued jobs execute locally:

```bash
./scripts/edge worker install-service --cloud
./scripts/edge worker start
./scripts/edge worker status
```

Generate a hosted report:

```bash
./scripts/edge report --cloud
```

## Scheduled Scans

The dashboard stores scan schedules in the Render Postgres database. A scheduler trigger must call
the API periodically so due schedules become queued scan jobs.

Minimum local/manual trigger:

```bash
./scripts/edge schedules run-due --cloud
```

Render cron option:

- Create a Render Cron Job.
- Schedule it every 5 minutes.
- Command:

```bash
curl -fsS -X POST "$SECOPSAI_EDGE_API_URL/api/v1/scan-schedules/run-due" \
  -H "Authorization: Bearer $SECOPSAI_ADMIN_TOKEN"
```

Set cron environment variables:

```text
SECOPSAI_EDGE_API_URL=https://<your-render-api>.onrender.com
SECOPSAI_ADMIN_TOKEN=<your-admin-token>
```

## Verification Checklist

- Render `/healthz` returns `{"status":"ok"}`.
- Cloudflare dashboard loads from the Pages URL.
- Settings > API Connection accepts the dashboard admin user login.
- Assets/Findings/Reports switch from `API not connected` to `Live API data` after connection.
- Local agent can register and scan with `--cloud`.
- Dashboard Scan Actions can queue a remote job, and the installed worker can claim it.
- Schedules page can create a daily/weekly schedule, and the cron trigger queues due jobs.
- Browser source and Cloudflare env vars do not contain `NEXT_PUBLIC_ADMIN_TOKEN`.
- Demo mode is unset or false for customer pilots.
