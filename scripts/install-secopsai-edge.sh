#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

info() {
  printf "\033[1;36m==>\033[0m %s\n" "$*"
}

warn() {
  printf "\033[1;33mwarning:\033[0m %s\n" "$*" >&2
}

ensure_nmap_hint() {
  if command -v nmap >/dev/null 2>&1; then
    return
  fi
  case "$(uname -s)" in
    Darwin)
      warn "Nmap is not installed. Run: brew install nmap"
      ;;
    Linux)
      warn "Nmap is not installed. Run: sudo apt-get update && sudo apt-get install -y nmap"
      ;;
    *)
      warn "Nmap is not installed. Install Nmap before running discovery scans."
      ;;
  esac
}

usage() {
  cat <<'EOF'
Install SecOpsAI Edge sensor

Usage:
  bash scripts/install-secopsai-edge.sh --cloud --api-url https://... --enrollment-token TOKEN

Options:
  --cloud              Configure hosted API mode
  --api-url URL        Render/FastAPI URL
  --admin-token TOKEN  API admin token
  --enrollment-token TOKEN
                       Short-lived, single-use customer enrollment token (recommended)
  --site-name NAME     Site name for this sensor
  --sensor-name NAME   Sensor display name
  --cidr CIDR          Optional first preview target
  --no-service         Do not install the background worker service
  --no-start           Install service but do not start it
EOF
}

main() {
  install_service="yes"
  start_service="yes"
  args=()

  while [ "$#" -gt 0 ]; do
    case "$1" in
      --help|-h)
        usage
        exit 0
        ;;
      --no-service)
        install_service="no"
        ;;
      --no-start)
        start_service="no"
        ;;
      *)
        args+=("$1")
        ;;
    esac
    shift || true
  done

  info "Installing SecOpsAI Edge from $ROOT_DIR"
  ensure_nmap_hint
  "$ROOT_DIR/scripts/edge" setup --sensor-only

  onboard_args=()
  if [ "${#args[@]}" -gt 0 ]; then
    onboard_args=("${args[@]}")
  fi
  if [ "$install_service" = "yes" ]; then
    onboard_args+=("--install-service")
  fi
  if [ "$start_service" = "yes" ]; then
    onboard_args+=("--start-service")
  fi
  if [ "${#onboard_args[@]}" -gt 0 ]; then
    "$ROOT_DIR/scripts/edge" onboard "${onboard_args[@]}"
  else
    "$ROOT_DIR/scripts/edge" onboard
  fi
  "$ROOT_DIR/scripts/edge" worker status || true

  info "SecOpsAI Edge install flow finished"
}

main "$@"
