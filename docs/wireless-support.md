# Wireless Inventory Support

SecOpsAI Edge wireless inventory is optional metadata collection. It records
SSID, BSSID, channel, signal in dBm, encryption, collection source, and the
observation time. It does not capture packet contents, join nearby networks,
inject frames, deauthenticate clients, or require monitor mode.

## Check Capability First

This command does not scan:

```bash
./scripts/edge wifi status
```

Linux sensors with more than one adapter should select the intended interface:

```bash
./scripts/edge wifi status --interface wlan1
export SECOPSAI_WIFI_INTERFACE=wlan1
```

The command exits `0` only when a supported backend and interface are present.
It exits `2` with a structured reason when collection is unsupported. Support
bundles include the same capability result without starting a Wi-Fi scan.

## macOS

The current adapter uses Apple's legacy `airport -s` inventory command when it
is present. New macOS releases may remove or restrict this private utility.
SecOpsAI reports that state instead of returning a misleading empty inventory.

An external USB Wi-Fi adapter is not required for Ethernet/LAN asset discovery.
SecOpsAI does not advertise TL-WN722N monitor mode on macOS.

## Linux And Raspberry Pi

Linux collection uses `iw` in managed mode and preserves the interface in the
source field, for example `linux:iw:wlan1`.

Install the maintained distribution package:

```bash
sudo apt-get update
sudo apt-get install -y iw
```

`iw dev <interface> scan` commonly requires `CAP_NET_ADMIN`. SecOpsAI does not
silently grant capabilities or run the entire Python worker as root. For a
controlled appliance, have an administrator review one narrow option such as a
root-owned helper or granting `cap_net_admin` to the distribution-managed `iw`
binary. Record and re-check that decision after package upgrades. A user-level
systemd worker without the approved permission will fail Wi-Fi jobs with an
actionable error while ordinary Nmap asset discovery remains available.

## TL-WN722N V4 Boundary

Support depends on the adapter's actual chipset, kernel, firmware, and driver.
SecOpsAI does not download third-party kernel modules, switch the adapter into
monitor mode, or claim injection support. Treat the sensor as Ethernet-first:

1. Attach the adapter to the Linux/Raspberry Pi sensor.
2. Confirm the kernel exposes a managed wireless interface with `iw dev`.
3. Run `./scripts/edge wifi status --interface <name>`.
4. Run one authorized Wi-Fi inventory job in the pilot location.
5. Record adapter USB identity, kernel, driver, firmware, interface, and result
   in the pilot acceptance evidence.

Fixture/parser tests prove the software contract. They are not a substitute
for this physical hardware and driver validation.

## Supported Result Semantics

- Signal is always stored as dBm. Percentage-only backends are not mixed into
  the same field.
- Hidden networks use the explicit SSID `<hidden>`.
- Encryption is normalized to `Open`, `WEP`, `WPA`, `WPA2`, or `WPA3` when the
  backend exposes enough information.
- The API stores collection provenance and exports it to SecOpsAI Core.
- A requested Wi-Fi scan that cannot run fails visibly; it never reports a
  successful empty inventory merely because a tool or permission is missing.
