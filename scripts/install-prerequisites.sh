#!/usr/bin/env bash
set -Eeuo pipefail

IFS=$'\n\t'

readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly TOOLS_DIR="${PROJECT_ROOT}/.tools"
readonly RALPHY_VENV="${TOOLS_DIR}/ralphy-venv"
readonly RALPHY_BIN="${TOOLS_DIR}/bin/ralphy"
readonly RALPHY_VERSION="${RALPHY_VERSION:-4.0.1}"
readonly PROXY_DIR="${HOME}/.cli-proxy-api"
readonly PROXY_CONFIG="${PROXY_DIR}/config.yaml"
readonly PROXY_ENV="${PROXY_DIR}/ralphthon.env"

LOGIN_AFTER_INSTALL=false

usage() {
  printf '%s\n' \
    "Usage: $0 [--login]" \
    "" \
    "Installs the macOS prerequisites for ralphthon-sample." \
    "  --login  Start CLIProxyAPI's interactive Claude OAuth login after setup."
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

if ! command -v claude >/dev/null 2>&1; then
  note "Installing Claude Code stable channel"
  brew install --cask claude-code
fi

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
printf 'export ANTHROPIC_BASE_URL=%q\n' 'http://127.0.0.1:8317' > "${PROXY_ENV}"
printf 'export ANTHROPIC_AUTH_TOKEN=%q\n' "${proxy_api_key}" >> "${PROXY_ENV}"
printf 'export RALPHY_BIN=%q\n' "${RALPHY_BIN}" >> "${PROXY_ENV}"
umask "${old_umask}"
chmod 600 "${PROXY_CONFIG}" "${PROXY_ENV}"

note "Starting CLIProxyAPI as a Homebrew service"
brew services restart cliproxyapi

if [[ "${LOGIN_AFTER_INSTALL}" == true ]]; then
  note "Starting interactive Claude OAuth login"
  cliproxyapi --config "${PROXY_CONFIG}" --claude-login
  brew services restart cliproxyapi
fi

note "Installed versions"
"${python_bin}" --version
uv --version
"${RALPHY_BIN}" --version
claude --version
brew list --versions cliproxyapi

printf '\n%s\n' \
  "Installation complete." \
  "Ralphy: ${RALPHY_BIN}" \
  "CLIProxyAPI config: ${PROXY_CONFIG}" \
  "Claude proxy environment: ${PROXY_ENV}" \
  "" \
  "If OAuth login was skipped, run:" \
  "  cliproxyapi --config \"${PROXY_CONFIG}\" --claude-login" \
  "" \
  "Before running Claude Code or Ralphy through the proxy:" \
  "  source \"${PROXY_ENV}\""
