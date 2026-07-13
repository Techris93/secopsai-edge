# Install SecOpsAI Edge Sensor

This guide installs a MacBook or Raspberry Pi/Linux machine as a SecOpsAI Edge sensor.

## MacBook Cloud Pilot

In the dashboard, select the customer workspace, open Sites, and click
`Enroll sensor` on the target site. Copy the one-time installer command. It
contains a 30-minute, single-use enrollment token and does not expose the
platform administrator token.

From the project folder, the copied command has this shape:

```bash
./scripts/install-secopsai-edge.sh \
  --cloud \
  --api-url https://secopsai-edge-api.onrender.com \
  --enrollment-token <one-time-token> \
  --sensor-name "MacBook Sensor"
```

The installer:

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
sudo apt-get install -y nmap python3 python3-venv nodejs npm
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

## Manual Onboarding

```bash
./scripts/edge onboard --cloud --api-url https://<api> \
  --enrollment-token <one-time-token> --install-service --start-service
```

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
./scripts/edge worker stop
rm -f ~/Library/LaunchAgents/ai.secopsai.edge.plist
rm -rf ~/Library/Logs/secopsai-edge
```

Linux:

```bash
systemctl --user disable --now ai.secopsai.edge.service
rm -f ~/.config/systemd/user/ai.secopsai.edge.service
systemctl --user daemon-reload
```
