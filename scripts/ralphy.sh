#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly RALPHY_BIN="${PROJECT_ROOT}/.tools/bin/ralphy"
readonly PROVIDER_FILE="${PROJECT_ROOT}/.tools/provider"
readonly CLAUDE_PROXY_ENV="${HOME}/.cli-proxy-api/ralphthon-claude.env"
readonly CODEX_HOME_DIR="${PROJECT_ROOT}/.tools/codex-home"

if [[ ! -x "${RALPHY_BIN}" ]]; then
  printf 'ERROR: PyPI ralphy is not installed. Run ./scripts/install-prerequisites.sh --provider claude|codex first.\n' >&2
  exit 1
fi

engine=""
seen_claude=false
seen_codex=false
for argument in "$@"; do
  case "${argument}" in
    --claude)
      engine="claude"
      seen_claude=true
      ;;
    --codex)
      engine="codex"
      seen_codex=true
      ;;
  esac
done

if [[ "${seen_claude}" == true && "${seen_codex}" == true ]]; then
  printf 'ERROR: Choose only one Ralphy engine: --claude or --codex.\n' >&2
  exit 1
fi

if [[ -z "${engine}" && -f "${PROVIDER_FILE}" ]]; then
  engine="$(<"${PROVIDER_FILE}")"
  [[ "${engine}" == "both" ]] && engine="claude"
  [[ "${engine}" == "skip" ]] && engine=""
fi

case "${engine}" in
  ""|claude|codex) ;;
  *)
    printf 'ERROR: Invalid provider in .tools/provider: %s\n' "${engine}" >&2
    exit 1
    ;;
esac

case "${engine}" in
  claude)
    if [[ ! -f "${CLAUDE_PROXY_ENV}" ]]; then
      printf 'ERROR: Claude proxy environment is missing. Re-run the prerequisite installer.\n' >&2
      exit 1
    fi
    # This generated file only exports the localhost proxy URL and its local key.
    # shellcheck disable=SC1090
    source "${CLAUDE_PROXY_ENV}"
    ;;
  codex)
    if [[ ! -f "${CODEX_HOME_DIR}/config.toml" || ! -f "${CODEX_HOME_DIR}/auth.json" ]]; then
      printf 'ERROR: Project-local Codex proxy config is missing. Re-run the prerequisite installer.\n' >&2
      exit 1
    fi
    export CODEX_HOME="${CODEX_HOME_DIR}"
    ;;
esac

exec "${RALPHY_BIN}" "$@"
