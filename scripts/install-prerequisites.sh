#!/usr/bin/env bash
set -Eeuo pipefail

IFS=$'\n\t'

readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly TOOLS_DIR="${PROJECT_ROOT}/.tools"
readonly RALPHY_VENV="${TOOLS_DIR}/ralphy-venv"
readonly RALPHY_BIN="${TOOLS_DIR}/bin/ralphy"
readonly RALPHY_VERSION="${RALPHY_VERSION:-4.0.1}"
readonly PROVIDER_FILE="${TOOLS_DIR}/provider"
readonly CODEX_HOME_DIR="${TOOLS_DIR}/codex-home"
readonly PROXY_DIR="${HOME}/.cli-proxy-api"
readonly PROXY_CONFIG="${PROXY_DIR}/config.yaml"
readonly CLAUDE_PROXY_ENV="${PROXY_DIR}/ralphthon-claude.env"

PROVIDER=""
LOGIN_AFTER_INSTALL=false

usage() {
  printf '%s\n' \
    "Usage: $0 --provider <claude|codex|both|skip> [--login]" \
    "" \
    "Installs the macOS prerequisites for ralphthon-sample." \
    "  --provider  Choose which AI CLI and CLIProxyAPI provider to prepare." \
    "  --login     Start the selected provider's interactive OAuth login." \
    "" \
    "Examples:" \
    "  $0 --provider claude --login" \
    "  $0 --provider codex --login" \
    "  $0 --provider both" \
    "  $0 --provider skip"
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

note() {
  printf '==> %s\n' "$*"
}

while (($# > 0)); do
  case "$1" in
    --provider)
      (($# >= 2)) || die "--provider requires a value"
      PROVIDER="$2"
      shift
      ;;
    --provider=*)
      PROVIDER="${1#*=}"
      ;;
    --login)
      LOGIN_AFTER_INSTALL=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      die "unknown option: $1"
      ;;
  esac
  shift
done

[[ -n "${PROVIDER}" ]] || {
  usage >&2
  die "choose --provider claude, codex, both, or skip"
}

case "${PROVIDER}" in
  claude|codex|both|skip) ;;
  *) die "unsupported provider: ${PROVIDER}" ;;
esac

if [[ "${PROVIDER}" == "skip" && "${LOGIN_AFTER_INSTALL}" == true ]]; then
  die "--login cannot be combined with --provider skip"
fi

if [[ "${EUID}" -eq 0 ]]; then
  die "run this script as your normal user, not root"
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  die "this installer currently supports macOS only; see README.md for manual links"
fi

command -v brew >/dev/null 2>&1 || die "Homebrew is required: https://brew.sh/"
command -v git >/dev/null 2>&1 || die "git is required"
command -v openssl >/dev/null 2>&1 || die "openssl is required"

python_bin="$(command -v python3 || true)"
if [[ -z "${python_bin}" ]] || ! "${python_bin}" -c 'import sys; raise SystemExit(sys.version_info < (3, 12))'; then
  note "Installing Python 3.12 with Homebrew"
  brew install python@3.12
  python_bin="$(brew --prefix python@3.12)/bin/python3.12"
fi

if ! command -v uv >/dev/null 2>&1; then
  note "Installing uv"
  brew install uv
fi

case "${PROVIDER}" in
  claude|both)
    if ! command -v claude >/dev/null 2>&1; then
      note "Installing Claude Code stable channel"
      brew install --cask claude-code
    fi
    ;;
esac

case "${PROVIDER}" in
  codex|both)
    if ! command -v codex >/dev/null 2>&1; then
      note "Installing Codex CLI"
      brew install --cask codex
    fi
    ;;
esac

if ! command -v cliproxyapi >/dev/null 2>&1; then
  note "Installing CLIProxyAPI"
  brew install cliproxyapi
fi

note "Installing PyPI ralphy ${RALPHY_VERSION} in a project-local virtual environment"
mkdir -p "${TOOLS_DIR}/bin"
if [[ ! -x "${RALPHY_VENV}/bin/python" ]]; then
  "${python_bin}" -m venv "${RALPHY_VENV}"
fi
"${RALPHY_VENV}/bin/python" -m pip install --upgrade pip
"${RALPHY_VENV}/bin/python" -m pip install --upgrade "ralphy==${RALPHY_VERSION}"
ln -sfn "../ralphy-venv/bin/ralphy" "${RALPHY_BIN}"

note "Preparing a localhost-only CLIProxyAPI configuration"
mkdir -p "${PROXY_DIR}"
chmod 700 "${PROXY_DIR}"

proxy_api_key=""
if [[ ! -f "${PROXY_CONFIG}" ]]; then
  proxy_api_key="sk-local-$(openssl rand -hex 24)"
  old_umask="$(umask)"
  umask 077
  printf '%s\n' \
    'host: "127.0.0.1"' \
    'port: 8317' \
    'tls:' \
    '  enable: false' \
    '  cert: ""' \
    '  key: ""' \
    'remote-management:' \
    '  allow-remote: false' \
    '  secret-key: ""' \
    '  disable-control-panel: true' \
    'auth-dir: "~/.cli-proxy-api"' \
    'api-keys:' \
    "  - \"${proxy_api_key}\"" \
    'debug: false' \
    'logging-to-file: true' \
    'usage-statistics-enabled: false' \
    'request-retry: 1' > "${PROXY_CONFIG}"
  umask "${old_umask}"
else
  proxy_api_key="$(awk '/^[[:space:]]*-[[:space:]]*"sk-/{value=$0; sub(/^[[:space:]]*-[[:space:]]*"/, "", value); sub(/"[[:space:]]*$/, "", value); print value; exit}' "${PROXY_CONFIG}")"
  [[ -n "${proxy_api_key}" ]] || die "existing ${PROXY_CONFIG} has no quoted sk-* api key; preserve it and configure manually"
fi

brew_config="$(brew --prefix)/etc/cliproxyapi.conf"
if [[ -e "${brew_config}" && ! -L "${brew_config}" ]]; then
  backup_path="${brew_config}.bak.$(date +%Y%m%d-%H%M%S)"
  note "Preserving existing Homebrew config at ${backup_path}"
  mv "${brew_config}" "${backup_path}"
fi
ln -sfn "${PROXY_CONFIG}" "${brew_config}"

old_umask="$(umask)"
umask 077
printf 'export ANTHROPIC_BASE_URL=%q\n' 'http://127.0.0.1:8317' > "${CLAUDE_PROXY_ENV}"
printf 'export ANTHROPIC_AUTH_TOKEN=%q\n' "${proxy_api_key}" >> "${CLAUDE_PROXY_ENV}"
printf 'export RALPHY_BIN=%q\n' "${RALPHY_BIN}" >> "${CLAUDE_PROXY_ENV}"

mkdir -p "${CODEX_HOME_DIR}"
printf '%s\n' \
  'model_provider = "cliproxyapi"' \
  'model = "gpt-5.6-sol"' \
  'model_reasoning_effort = "high"' \
  '' \
  '[model_providers.cliproxyapi]' \
  'name = "cliproxyapi"' \
  'base_url = "http://127.0.0.1:8317/v1"' \
  'wire_api = "responses"' \
  'http_headers = { "X-OpenAI-Actor-Authorization" = "local-proxy" }' > "${CODEX_HOME_DIR}/config.toml"
printf '{\n  "OPENAI_API_KEY": "%s"\n}\n' "${proxy_api_key}" > "${CODEX_HOME_DIR}/auth.json"
printf '%s\n' "${PROVIDER}" > "${PROVIDER_FILE}"
umask "${old_umask}"
chmod 600 \
  "${PROXY_CONFIG}" \
  "${CLAUDE_PROXY_ENV}" \
  "${CODEX_HOME_DIR}/config.toml" \
  "${CODEX_HOME_DIR}/auth.json" \
  "${PROVIDER_FILE}"

note "Starting CLIProxyAPI as a Homebrew service"
brew services restart cliproxyapi

if [[ "${LOGIN_AFTER_INSTALL}" == true ]]; then
  case "${PROVIDER}" in
    claude)
      note "Starting interactive Claude Code provider OAuth login"
      cliproxyapi --config "${PROXY_CONFIG}" --claude-login
      ;;
    codex)
      note "Starting interactive ChatGPT/Codex provider OAuth login"
      cliproxyapi --config "${PROXY_CONFIG}" --codex-login
      ;;
    both)
      note "Starting interactive Claude Code provider OAuth login"
      cliproxyapi --config "${PROXY_CONFIG}" --claude-login
      note "Starting interactive ChatGPT/Codex provider OAuth login"
      cliproxyapi --config "${PROXY_CONFIG}" --codex-login
      ;;
  esac
  brew services restart cliproxyapi
fi

note "Installed versions"
"${python_bin}" --version
uv --version
"${RALPHY_BIN}" --version
case "${PROVIDER}" in
  claude) claude --version ;;
  codex) codex --version ;;
  both)
    claude --version
    codex --version
    ;;
  skip) note "AI CLI installation skipped" ;;
esac
brew list --versions cliproxyapi

printf '\n%s\n' \
  "Installation complete." \
  "Selected provider: ${PROVIDER}" \
  "Ralphy: ${RALPHY_BIN}" \
  "CLIProxyAPI config: ${PROXY_CONFIG}" \
  "Claude proxy environment: ${CLAUDE_PROXY_ENV}" \
  "Project-local Codex home: ${CODEX_HOME_DIR}"

if [[ "${LOGIN_AFTER_INSTALL}" == false && "${PROVIDER}" != "skip" ]]; then
  printf '\n%s\n' \
    "OAuth login was skipped. Run one of the matching commands from README.md before using Ralphy."
fi
