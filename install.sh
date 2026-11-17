#!/usr/bin/env bash
# One entry point for a fresh Fedora workstation; see bootstrap/README.md.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$script_dir/bootstrap/setup.py" "$@"
