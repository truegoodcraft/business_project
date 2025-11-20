#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") [-n|--dry-run]
  -n, --dry-run   Print the planned file operations without executing them.
USAGE
}

DRY_RUN=0
if [[ ${1:-} == "-n" || ${1:-} == "--dry-run" ]]; then
  DRY_RUN=1
elif [[ $# -gt 0 ]]; then
  usage
  exit 1
fi

run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    eval "$@"
  fi
}

note() {
  printf '\n==> %s\n' "$1"
}

note "Ensuring core/services layout"
run "mkdir -p core/services/capabilities"

if [[ -f core/conn_broker.py && ! -f core/services/conn_broker.py ]]; then
  note "Moving core/conn_broker.py into core/services/"
  run "git mv core/conn_broker.py core/services/conn_broker.py"
fi

if [[ -d core/capabilities && -f core/capabilities/__init__.py && ! -f core/services/capabilities/__init__.py ]]; then
  note "Relocating core/capabilities package into service layer"
  run "git mv core/capabilities/__init__.py core/services/capabilities/__init__.py"
fi
if [[ -d core/capabilities && -f core/capabilities/api.py && ! -f core/services/capabilities/api.py ]]; then
  run "git mv core/capabilities/api.py core/services/capabilities/api.py"
fi
if [[ -d core/capabilities && -f core/capabilities/registry.py && ! -f core/services/capabilities/registry.py ]]; then
  run "git mv core/capabilities/registry.py core/services/capabilities/registry.py"
fi

note "Renaming plugins_alpha directory"
if [[ -d plugins_alpha && ! -d plugins ]]; then
  run "git mv plugins_alpha plugins"
fi

note "Re-homing maintenance scripts"
if [[ -d tools ]]; then
  run "git mv tools/add_spdx_headers.py scripts/add_spdx_headers.py"
  run "git mv tools/check_spdx_headers.py scripts/check_spdx_headers.py"
  run "git mv tools/check_licenses.py scripts/check_licenses.py"
  if [[ -f tools/launch_buscore.ps1 ]]; then
    run "git mv tools/launch_buscore.ps1 scripts/launch_buscore.ps1"
  fi
  run "rmdir tools 2>/dev/null || true"
fi

note "Staging docs directory moves"
for file in LICENSE LICENSE-THIRD-PARTY.md PLUGINS_LICENSE; do
  if [[ -f $file ]]; then
    run "git mv $file docs/$file"
  fi
done

note "Done. Review git status for remaining manual edits."
