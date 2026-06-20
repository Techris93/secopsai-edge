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
   - `SECOPSAI_ADMIN_TOKEN`: a long random operator token.
   - `SECOPSAI_CORS_ORIGINS`: your Cloudflare Pages URL, plus local dev if needed.
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

## Cloudflare Pages Dashboard

Create a Pages project from the same Git repository.

Use these settings:

- Root directory: `web`
- Build command: `npm ci && npm run build`
- Build output directory: `out`
- Environment variable:
  - `NEXT_PUBLIC_API_BASE_URL=https://<your-render-api>.onrender.com`

The dashboard is a static Next.js export. It does not include `NEXT_PUBLIC_ADMIN_TOKEN`.
Open Settings in the dashboard and use the API Connection panel to create a browser session with
your Render API admin token.

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
./scripts/edge worker --cloud
```

Generate a hosted report:

```bash
./scripts/edge report --cloud
```

## Verification Checklist

- Render `/healthz` returns `{"status":"ok"}`.
- Cloudflare dashboard loads from the Pages URL.
- Settings > API Connection accepts the admin token.
- Assets/Findings/Reports switch from demo fallback to live API data after connection.
- Local agent can register and scan with `--cloud`.
- Dashboard Scan Actions can queue a remote job, and `./scripts/edge worker --cloud --once` can claim it.
- Browser source and Cloudflare env vars do not contain `NEXT_PUBLIC_ADMIN_TOKEN`.
