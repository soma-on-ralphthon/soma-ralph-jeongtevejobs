#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly RALPHY_BIN="${PROJECT_ROOT}/.tools/bin/ralphy"

if [[ ! -x "${RALPHY_BIN}" ]]; then
  printf 'ERROR: PyPI ralphy is not installed. Run ./scripts/install-prerequisites.sh first.\n' >&2
  exit 1
fi

exec "${RALPHY_BIN}" "$@"
