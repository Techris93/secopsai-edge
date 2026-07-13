#!/usr/bin/env bash
set -euo pipefail
umask 077

REPOSITORY="${SECOPSAI_EDGE_GITHUB_REPOSITORY:-Techris93/secopsai-edge}"
VERSION="latest"
INSTALL_DIR="${SECOPSAI_EDGE_INSTALL_DIR:-$HOME/.local/share/secopsai-edge}"
UPGRADE="no"
INSTALL_ARGS=()

fail() { printf "error: %s\n" "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Bootstrap SecOpsAI Edge from a verified GitHub release.

Usage:
  bash bootstrap-secopsai-edge.sh [--version 0.2.1] [--install-dir PATH]
    --cloud --api-url URL --enrollment-token TOKEN [installer options]

Options consumed by bootstrap:
  --version VERSION   Release version; defaults to latest
  --install-dir PATH  Installation directory
  --upgrade           Replace an existing installation and preserve credential files

All remaining options are passed to install-secopsai-edge.sh.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --version) shift; VERSION="${1:-}"; [ -n "$VERSION" ] || fail "--version requires a value" ;;
    --install-dir) shift; INSTALL_DIR="${1:-}"; [ -n "$INSTALL_DIR" ] || fail "--install-dir requires a value" ;;
    --upgrade) UPGRADE="yes" ;;
    *) INSTALL_ARGS+=("$1") ;;
  esac
  shift || true
done

command -v curl >/dev/null 2>&1 || fail "curl is required"
command -v shasum >/dev/null 2>&1 || fail "shasum is required"
command -v python3 >/dev/null 2>&1 || fail "python3 is required"
case "$VERSION" in v*) VERSION="${VERSION#v}" ;; esac

if [ "$VERSION" = "latest" ]; then
  base_url="https://github.com/$REPOSITORY/releases/latest/download"
  archive_name="secopsai-edge.tar.gz"
else
  base_url="https://github.com/$REPOSITORY/releases/download/v$VERSION"
  archive_name="secopsai-edge-$VERSION.tar.gz"
fi

if [ -e "$INSTALL_DIR" ] && [ "$UPGRADE" != "yes" ]; then
  fail "$INSTALL_DIR already exists; use --upgrade to preserve credentials and replace it"
fi

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/secopsai-edge-install.XXXXXX")"
previous_dir=""
installed_new="no"
cleanup() {
  status=$?
  if [ "$status" -ne 0 ] && [ "$installed_new" = "yes" ]; then
    rm -rf "$INSTALL_DIR"
    if [ -n "$previous_dir" ] && [ -e "$previous_dir" ]; then
      mv "$previous_dir" "$INSTALL_DIR"
    fi
  fi
  rm -rf "$work_dir"
  return "$status"
}
trap cleanup EXIT

curl -fL --retry 3 --connect-timeout 15 --max-time 600 --proto '=https' --proto-redir '=https' --tlsv1.2 "$base_url/$archive_name" -o "$work_dir/$archive_name"
curl -fL --retry 3 --connect-timeout 15 --max-time 60 --proto '=https' --proto-redir '=https' --tlsv1.2 "$base_url/$archive_name.sha256" -o "$work_dir/$archive_name.sha256"
expected_checksum="$(CHECKSUM_FILE="$work_dir/$archive_name.sha256" ARCHIVE_NAME="$archive_name" python3 - <<'PY'
import os
import re

with open(os.environ["CHECKSUM_FILE"], encoding="ascii") as handle:
    fields = handle.read().strip().split()
if len(fields) != 2 or fields[1].lstrip("*") != os.environ["ARCHIVE_NAME"]:
    raise SystemExit("checksum manifest does not name the requested archive")
if not re.fullmatch(r"[0-9a-fA-F]{64}", fields[0]):
    raise SystemExit("checksum manifest does not contain a SHA-256 digest")
print(fields[0].lower())
PY
)"
actual_checksum="$(shasum -a 256 "$work_dir/$archive_name" | awk '{print tolower($1)}')"
[ "$actual_checksum" = "$expected_checksum" ] || fail "release checksum verification failed"

mkdir -p "$work_dir/extract"
ARCHIVE="$work_dir/$archive_name" EXTRACT_DIR="$work_dir/extract" python3 - <<'PY'
import os
import pathlib
import tarfile

archive = os.environ["ARCHIVE"]
extract_dir = os.environ["EXTRACT_DIR"]
with tarfile.open(archive, "r:gz") as bundle:
    members = bundle.getmembers()
    if not members:
        raise SystemExit("release archive is empty")
    roots: set[str] = set()
    for member in members:
        path = pathlib.PurePosixPath(member.name)
        if path.is_absolute() or not path.parts or ".." in path.parts:
            raise SystemExit(f"unsafe path in release archive: {member.name}")
        if member.issym() or member.islnk() or member.isdev() or member.isfifo():
            raise SystemExit(f"unsupported entry in release archive: {member.name}")
        roots.add(path.parts[0])
    if len(roots) != 1:
        raise SystemExit("release archive must contain exactly one package directory")
    bundle.extractall(extract_dir, members=members)
PY
source_dir="$(find "$work_dir/extract" -mindepth 1 -maxdepth 1 -type d -print -quit)"
[ -n "$source_dir" ] || fail "Release archive has no package directory"

if [ -e "$INSTALL_DIR" ]; then
  for credentials in .cloud.env .cloud-sensor.env .env .sensor.env; do
    if [ -f "$INSTALL_DIR/$credentials" ]; then
      cp "$INSTALL_DIR/$credentials" "$source_dir/$credentials"
      chmod 600 "$source_dir/$credentials"
    fi
  done
  previous_dir="$INSTALL_DIR.previous"
  rm -rf "$previous_dir"
  mv "$INSTALL_DIR" "$previous_dir"
fi

mkdir -p "$(dirname "$INSTALL_DIR")"
mv "$source_dir" "$INSTALL_DIR"
installed_new="yes"
chmod 700 "$INSTALL_DIR"

if [ "${#INSTALL_ARGS[@]}" -gt 0 ]; then
  "$INSTALL_DIR/scripts/install-secopsai-edge.sh" "${INSTALL_ARGS[@]}"
else
  "$INSTALL_DIR/scripts/install-secopsai-edge.sh"
fi
printf "SecOpsAI Edge installed at %s\n" "$INSTALL_DIR"
