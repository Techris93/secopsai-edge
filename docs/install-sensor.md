# Install SecOpsAI Edge Sensor

This guide installs a MacBook or Raspberry Pi/Linux machine as a SecOpsAI Edge sensor.

## MacBook Cloud Pilot

From the project folder:

```bash
./scripts/install-secopsai-edge.sh \
  --cloud \
  --api-url https://secopsai-edge-api.onrender.com \
  --admin-token <admin-token> \
  --site-name "Main Office" \
  --sensor-name "MacBook Sensor"
```

The installer:

- checks Python dependencies
- checks that Nmap is available
- registers the sensor
- saves `.cloud.env` and `.cloud-sensor.env`
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

Then run the same installer:

```bash
./scripts/install-secopsai-edge.sh \
  --cloud \
  --api-url https://secopsai-edge-api.onrender.com \
  --admin-token <admin-token> \
  --site-name "Branch Office" \
  --sensor-name "Pi Sensor"
```

On Linux, the worker installs as a user `systemd` service.

## Manual Onboarding

```bash
./scripts/edge onboard --cloud --install-service --start-service
```

Optional first target preview:

```bash
./scripts/edge onboard --cloud --cidr 192.168.1.0/24
```

Only preview or scan networks you own or are explicitly authorized to test.

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
