# Install SecOpsAI Edge Sensor

This guide installs a MacBook or Raspberry Pi/Linux machine as a SecOpsAI Edge sensor.

## MacBook Cloud Pilot

In the dashboard, select the customer workspace, open Sites, and click
`Enroll sensor` on the target site. Copy the one-time installer command. It
contains a 30-minute, single-use enrollment token and does not expose the
platform administrator token.

The copied command has this shape and does not require a repository clone:

```bash
gh auth login
gh release download --repo Techris93/secopsai-edge --pattern bootstrap-secopsai-edge.sh --clobber
bash bootstrap-secopsai-edge.sh \
  --cloud \
  --api-url https://secopsai-edge-api.onrender.com \
  --enrollment-token <one-time-token> \
  --sensor-name "MacBook Sensor"
```

The pilot repository is private. The installer therefore needs GitHub
collaborator access and an authenticated GitHub CLI. `gh auth login` stores the
GitHub credential outside the copied install command; the command contains only
the short-lived, single-use sensor enrollment token. When the repository is
public, the bootstrap can also be downloaded directly over HTTPS.

The installer:

- downloads the current GitHub release through authenticated GitHub CLI or HTTPS
- verifies the published SHA-256 checksum before extraction
- checks Python dependencies
- checks that Nmap is available
- registers the sensor
- exchanges the one-time enrollment token and saves only the resulting sensor
  credential in `.cloud-sensor.env`
- installs the worker as a launchd service
- starts the worker

Worker logs on macOS:

```bash
./scripts/edge worker logs
```

Worker status:

```bash
./scripts/edge worker status
```

## Linux / Raspberry Pi

Install Nmap first:

```bash
sudo apt-get update
sudo apt-get install -y nmap iw python3 python3-venv nodejs npm
```

Create the enrollment from the target customer workspace and run the same
copied installer:

```bash
./scripts/install-secopsai-edge.sh \
  --cloud \
  --api-url https://secopsai-edge-api.onrender.com \
  --enrollment-token <one-time-token> \
  --sensor-name "Pi Sensor"
```

On Linux, the worker installs as a user `systemd` service.

Check wireless support without scanning:

```bash
./scripts/edge wifi status --interface wlan1
```

Wi-Fi collection is optional and often needs a reviewed `CAP_NET_ADMIN`
configuration. The installer does not grant it or run the worker as root. See
[Wireless Inventory Support](wireless-support.md) before enabling Wi-Fi jobs.

Use `--version 0.3.9` to pin this pilot build. Use `--upgrade` for an existing
installation; the bootstrap preserves credential files, keeps the previous
installation as `.previous`, and restores it automatically if the new
installer fails.

## Manual Onboarding

For a background worker, use the released bootstrap command above. The source
checkout path is suitable for a foreground development worker only:

```bash
./scripts/edge onboard --cloud --api-url https://<api> \
  --enrollment-token <one-time-token>
```

Do not use `--install-service` from a checkout stored under macOS
`~/Documents`, `~/Desktop`, `~/Downloads`, or iCloud Drive. launchd may be
blocked by macOS privacy controls once the terminal closes. Use the released
installer, which places the runtime under `~/.local/share/secopsai-edge`, or
move the checkout outside protected folders. The helper rejects the protected
source-tree case by default and prints the recovery path.

Optional first target preview:

```bash
./scripts/edge onboard --cloud --api-url https://<api> \
  --enrollment-token <one-time-token> --cidr 192.168.1.0/24
```

Only preview or scan networks you own or are explicitly authorized to test.

The legacy `--admin-token` registration path remains available for Default
Workspace recovery and automation. Do not give that token to a pilot customer.
Unused enrollments can be revoked from Sites; used, expired, and revoked tokens
cannot register another sensor.

## Uninstall

macOS:

```bash
./scripts/edge worker uninstall
rm -rf ~/Library/Logs/secopsai-edge
```

Linux:

```bash
./scripts/edge worker uninstall
```
