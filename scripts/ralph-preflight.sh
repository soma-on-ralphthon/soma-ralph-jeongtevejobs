#!/usr/bin/env bash
#
# Ralph/Ralphy preflight.
#
#   ./scripts/ralph-preflight.sh plan   tasks.yaml
#   ./scripts/ralph-preflight.sh setup  tasks.yaml
#   ./scripts/ralph-preflight.sh verify tasks.yaml
#   ./scripts/ralph-preflight.sh run    tasks.yaml -- <ralphy options>
#
# 계약 파일은 ralph.environment.json이다. runtime artifact는 .ralphy/preflight/ 아래에만 쓴다.
# secret 값은 읽지도 출력하지도 않는다. 존재 여부, 파일 권한, 변수 이름만 확인한다.
#
# macOS 기본 bash가 3.2.57이라 bash 4 문법(연관 배열, mapfile, ${var^^})을 쓰지 않는다.
# eval을 쓰지 않는다. 모든 외부 명령은 인용된 인자로 직접 호출한다.

set -Eeuo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

readonly SCRIPT_PATH="${BASH_SOURCE[0]}"
readonly SCRIPT_NAME="$(basename "${SCRIPT_PATH}")"
readonly CONTRACT_BASENAME="ralph.environment.json"
readonly ARTIFACTS_SUBDIR=".ralphy/preflight"
readonly CLIPROXY_PORT="8317"
readonly CLIPROXY_HOST="127.0.0.1"
readonly MIN_PYTHON_MAJOR="3"
readonly MIN_PYTHON_MINOR="12"
readonly RALPHY_DRY_RUN_TIMEOUT="120"
readonly QUALITY_GATE_TIMEOUT="900"

# 결과 버킷.
#   BLOCKERS       setup으로 고칠 수 없다. 즉시 중단한다.
#   INSTALLS       setup의 uv sync --frozen으로 고칠 수 있다.
#   USER_ACTIONS   사용자만 실행할 수 있다. sudo, secret, OAuth, git identity.
#   WARNINGS       실행을 막지 않는다. 기록만 한다.
BLOCKERS=()
INSTALLS=()
USER_ACTIONS=()
WARNINGS=()
REPORT=()

PROJECT_ROOT=""
CONTRACT_FILE=""
ARTIFACTS_DIR=""
LOGS_DIR=""
REPORT_FILE=""
PASSED_FILE=""
FINGERPRINT_FILE=""
PRIVILEGED_FILE=""
TASKS_FILE="tasks.yaml"
PROVIDER=""
PASSTHROUGH=()
PY_BIN=""
HASH_CMD=""

# ---------------------------------------------------------------------------
# 출력 도우미
# ---------------------------------------------------------------------------

note() { printf '==> %s\n' "$*"; }

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

on_error() {
  printf 'ERROR: %s failed at line %s (exit %s)\n' "${SCRIPT_NAME}" "$2" "$1" >&2
}
trap 'on_error "$?" "${LINENO}"' ERR

usage() {
  printf '%s\n' \
    "Usage: ${SCRIPT_NAME} <plan|setup|verify|run> [tasks-file] [-- <ralphy options>]" \
    "" \
    "  plan    설치 없이 정적 분석만 수행하고 ${ARTIFACTS_SUBDIR}/report.md를 만든다." \
    "  setup   plan 통과 후 uv sync --frozen으로 lockfile 기반 설치만 수행한다." \
    "  verify  전체 환경을 검증하고 통과하면 ${ARTIFACTS_SUBDIR}/PASSED를 남긴다." \
    "  run     verify를 다시 수행하고 통과할 때만 scripts/ralphy.sh를 실행한다." \
    "" \
    "Examples:" \
    "  ${SCRIPT_NAME} plan tasks.yaml" \
    "  ${SCRIPT_NAME} setup tasks.yaml" \
    "  ${SCRIPT_NAME} verify tasks.yaml" \
    "  ${SCRIPT_NAME} run tasks.yaml -- --claude --yaml tasks.yaml --max-iterations 1 --no-commit"
}

# ---------------------------------------------------------------------------
# 결과 기록
# ---------------------------------------------------------------------------

record() {  # record <PASS|FAIL|WARN|SKIP> <label> <detail>
  REPORT+=("$1|$2|$3")
  printf '  [%-4s] %s%s\n' "$1" "$2" "${3:+ — $3}"
}

add_blocker()     { BLOCKERS+=("$1|$2"); }      # <설명>|<사용자가 실행할 해결 명령>
add_install()     { INSTALLS+=("$1|$2"); }
add_user_action() { USER_ACTIONS+=("$1|$2"); }
add_warning()     { WARNINGS+=("$1|$2"); }

count_of() {  # 빈 배열도 set -u에서 안전하게 센다.
  case "$1" in
    BLOCKERS)     printf '%s\n' "${#BLOCKERS[@]}" ;;
    INSTALLS)     printf '%s\n' "${#INSTALLS[@]}" ;;
    USER_ACTIONS) printf '%s\n' "${#USER_ACTIONS[@]}" ;;
    WARNINGS)     printf '%s\n' "${#WARNINGS[@]}" ;;
    *)            printf '0\n' ;;
  esac
}

entry_at() {  # entry_at <bucket> <index>
  case "$1" in
    BLOCKERS)     printf '%s\n' "${BLOCKERS[$2]}" ;;
    INSTALLS)     printf '%s\n' "${INSTALLS[$2]}" ;;
    USER_ACTIONS) printf '%s\n' "${USER_ACTIONS[$2]}" ;;
    WARNINGS)     printf '%s\n' "${WARNINGS[$2]}" ;;
  esac
}

reset_results() {
  BLOCKERS=()
  INSTALLS=()
  USER_ACTIONS=()
  WARNINGS=()
  REPORT=()
}

# ---------------------------------------------------------------------------
# 부트스트랩
# ---------------------------------------------------------------------------

refuse_root() {
  if [[ "$(id -u)" -eq 0 ]]; then
    die "run this script as your normal user, not root. 전체 script의 sudo 실행은 금지다."
  fi
}

resolve_project_root() {
  local script_dir root
  script_dir="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
  if root="$(git -C "${script_dir}" rev-parse --show-toplevel 2>/dev/null)"; then
    printf '%s\n' "${root}"
    return 0
  fi
  printf '%s\n' "$(cd "${script_dir}/.." && pwd)"
}

pick_python() {
  local candidate
  for candidate in \
    "${PROJECT_ROOT}/.venv/bin/python" \
    "$(command -v python3 2>/dev/null || true)" \
    "$(command -v python 2>/dev/null || true)"
  do
    [[ -n "${candidate}" && -x "${candidate}" ]] || continue
    printf '%s\n' "${candidate}"
    return 0
  done
  return 1
}

pick_hash_cmd() {
  if command -v shasum >/dev/null 2>&1; then
    printf 'shasum\n'
  elif command -v sha256sum >/dev/null 2>&1; then
    printf 'sha256sum\n'
  else
    return 1
  fi
}

bootstrap() {
  refuse_root
  PROJECT_ROOT="$(resolve_project_root)"
  cd "${PROJECT_ROOT}"

  CONTRACT_FILE="${PROJECT_ROOT}/${CONTRACT_BASENAME}"
  ARTIFACTS_DIR="${PROJECT_ROOT}/${ARTIFACTS_SUBDIR}"
  LOGS_DIR="${ARTIFACTS_DIR}/logs"
  REPORT_FILE="${ARTIFACTS_DIR}/report.md"
  PASSED_FILE="${ARTIFACTS_DIR}/PASSED"
  FINGERPRINT_FILE="${ARTIFACTS_DIR}/fingerprint.txt"
  PRIVILEGED_FILE="${ARTIFACTS_DIR}/privileged-actions.sh"

  mkdir -p "${LOGS_DIR}"

  PY_BIN="$(pick_python || true)"
  HASH_CMD="$(pick_hash_cmd || true)"
}

# ---------------------------------------------------------------------------
# 저수준 유틸
# ---------------------------------------------------------------------------

# 상위 셸의 VIRTUAL_ENV가 프로젝트 .venv와 다르면 uv가 경고를 낸다. 항상 제거하고 호출한다.
run_uv()    { env -u VIRTUAL_ENV uv "$@"; }
run_clean() { env -u VIRTUAL_ENV "$@"; }

# eval 없이 타임아웃을 건다. macOS 기본 환경에 timeout(1)이 없다.
run_with_timeout() {  # run_with_timeout <seconds> <logfile> <command...>
  local seconds="$1"; shift
  local logfile="$1"; shift
  local child_pid watchdog_pid status

  "$@" >"${logfile}" 2>&1 &
  child_pid=$!
  ( sleep "${seconds}"; kill -TERM "${child_pid}" 2>/dev/null || true ) &
  watchdog_pid=$!

  status=0
  wait "${child_pid}" || status=$?

  kill -TERM "${watchdog_pid}" 2>/dev/null || true
  wait "${watchdog_pid}" 2>/dev/null || true
  return "${status}"
}

hash_file() {
  local target="$1"
  [[ -f "${target}" ]] || { printf 'missing\n'; return 0; }
  case "${HASH_CMD}" in
    shasum)    shasum -a 256 "${target}" | awk '{print $1}' ;;
    sha256sum) sha256sum "${target}" | awk '{print $1}' ;;
    *)         printf 'nohash\n' ;;
  esac
}

hash_string() {
  case "${HASH_CMD}" in
    shasum)    printf '%s' "$1" | shasum -a 256 | awk '{print $1}' ;;
    sha256sum) printf '%s' "$1" | sha256sum | awk '{print $1}' ;;
    *)         printf 'nohash\n' ;;
  esac
}

file_mode() {
  local target="$1"
  [[ -e "${target}" ]] || { printf 'missing\n'; return 0; }
  if stat -f '%Lp' "${target}" 2>/dev/null; then
    return 0
  fi
  stat -c '%a' "${target}" 2>/dev/null || printf 'unknown\n'
}

utc_now() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

expand_home() {  # ~/... 를 절대 경로로 바꾼다. eval을 쓰지 않는다.
  case "$1" in
    "~/"*) printf '%s/%s\n' "${HOME}" "${1#\~/}" ;;
    "~")   printf '%s\n' "${HOME}" ;;
    *)     printf '%s\n' "$1" ;;
  esac
}

# ralph.environment.json에서 dotted path 하나를 읽는다. 값은 argv로만 전달하므로 주입이 없다.
contract_get() {  # contract_get <dotted.path> [default]
  local path="$1"
  local fallback="${2-}"

  if [[ -z "${PY_BIN}" || ! -f "${CONTRACT_FILE}" ]]; then
    printf '%s\n' "${fallback}"
    return 0
  fi

  "${PY_BIN}" - "${CONTRACT_FILE}" "${path}" "${fallback}" <<'PYTHON' 2>/dev/null || printf '%s\n' "${fallback}"
import json
import sys

contract_file, dotted_path, fallback = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(contract_file, encoding="utf-8") as handle:
        current = json.load(handle)
    for part in dotted_path.split("."):
        if not part:
            continue
        current = current[int(part)] if isinstance(current, list) else current[part]
except Exception:
    print(fallback)
    sys.exit(0)

if isinstance(current, list):
    for item in current:
        print(" ".join(str(x) for x in item) if isinstance(item, list) else item)
elif isinstance(current, bool):
    print("true" if current else "false")
elif current is None:
    print(fallback)
else:
    print(current)
PYTHON
}

contract_is_valid_json() {
  [[ -n "${PY_BIN}" ]] || return 0
  "${PY_BIN}" -c 'import json,sys; json.load(open(sys.argv[1], encoding="utf-8"))' "${CONTRACT_FILE}" >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# 정적 분석 — 저장소 구조
# ---------------------------------------------------------------------------

check_git_repository() {
  if ! git -C "${PROJECT_ROOT}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    record FAIL "git repository" "${PROJECT_ROOT} is not a git work tree"
    add_blocker "git 저장소가 아니다: ${PROJECT_ROOT}" "git -C '${PROJECT_ROOT}' init"
    return 0
  fi
  record PASS "git repository" "${PROJECT_ROOT}"

  local probe="${ARTIFACTS_DIR}/.write-probe"
  if ( : >"${probe}" ) 2>/dev/null; then
    rm -f "${probe}"
    record PASS "worktree writable" "${ARTIFACTS_SUBDIR} is writable"
  else
    record FAIL "worktree writable" "cannot write to ${ARTIFACTS_SUBDIR}"
    add_blocker "작업 트리에 쓸 수 없다: ${ARTIFACTS_DIR}" "chmod u+w '${PROJECT_ROOT}'"
  fi
}

check_required_files() {
  local required_file
  for required_file in \
    "${TASKS_FILE}" \
    "pyproject.toml" \
    "uv.lock" \
    "scripts/check.sh" \
    "scripts/ralphy.sh" \
    "scripts/install-prerequisites.sh" \
    ".ralphy/config.yaml" \
    "${CONTRACT_BASENAME}"
  do
    if [[ -f "${PROJECT_ROOT}/${required_file}" ]]; then
      record PASS "file ${required_file}" ""
    else
      record FAIL "file ${required_file}" "missing"
      add_blocker "필수 파일이 없다: ${required_file}" "git -C '${PROJECT_ROOT}' status"
    fi
  done

  local executable_script
  for executable_script in "scripts/check.sh" "scripts/ralphy.sh"; do
    [[ -f "${PROJECT_ROOT}/${executable_script}" ]] || continue
    if [[ -x "${PROJECT_ROOT}/${executable_script}" ]]; then
      record PASS "exec bit ${executable_script}" ""
    else
      record FAIL "exec bit ${executable_script}" "not executable"
      add_blocker "${executable_script}에 실행 권한이 없다" "chmod +x '${PROJECT_ROOT}/${executable_script}'"
    fi
  done
}

check_contract_file() {
  if [[ ! -f "${CONTRACT_FILE}" ]]; then
    record FAIL "contract ${CONTRACT_BASENAME}" "missing"
    add_blocker "${CONTRACT_BASENAME}이 없다" "PREFLIGHTS.md의 절차로 계약 파일을 다시 만들어라"
    return 0
  fi
  if contract_is_valid_json; then
    record PASS "contract ${CONTRACT_BASENAME}" "valid json, version $(contract_get contract_version 0)"
  else
    record FAIL "contract ${CONTRACT_BASENAME}" "invalid json"
    add_blocker "${CONTRACT_BASENAME} JSON 파싱 실패" "python3 -m json.tool '${CONTRACT_FILE}'"
  fi
}

check_tasks_file() {
  local tasks_path="${PROJECT_ROOT}/${TASKS_FILE}"
  if [[ ! -f "${tasks_path}" ]]; then
    record FAIL "tasks file" "${TASKS_FILE} missing"
    add_blocker "task 파일이 없다: ${TASKS_FILE}" "ls -la '${PROJECT_ROOT}'"
    return 0
  fi

  local total done_count pending_count
  total="$(grep -cE '^[[:space:]]*-[[:space:]]+title:' "${tasks_path}" || true)"
  done_count="$(grep -cE '^[[:space:]]*completed:[[:space:]]*true' "${tasks_path}" || true)"
  pending_count=$(( total - done_count ))

  if [[ "${total}" -eq 0 ]]; then
    record FAIL "tasks file" "no task entries found in ${TASKS_FILE}"
    add_blocker "${TASKS_FILE}에 task가 없다" "cat '${tasks_path}'"
    return 0
  fi
  record PASS "tasks file" "${total} tasks, ${done_count} completed, ${pending_count} pending"

  if [[ "${pending_count}" -le 0 ]]; then
    add_warning "모든 task가 completed 상태다. Ralphy가 실행할 일이 없다." "cat '${tasks_path}'"
  fi
}

# ---------------------------------------------------------------------------
# 정적 분석 — manifest와 lockfile
# ---------------------------------------------------------------------------

is_declared_in_manifest() {
  grep -qE "^[[:space:]]*\"$1([><=!~,[:space:]\"]|$)" "${PROJECT_ROOT}/pyproject.toml"
}

# scripts/check.sh를 재귀적으로 읽어 실제로 쓰이는 command를 뽑는다.
collect_quality_tools() {
  local script="$1"
  [[ -f "${script}" ]] || return 0
  grep -oE 'uv run [a-zA-Z][a-zA-Z0-9_.-]*' "${script}" | awk '{print $3}' | sort -u
}

check_quality_script_dependencies() {
  local gate="${PROJECT_ROOT}/scripts/check.sh"
  if [[ ! -f "${gate}" ]]; then
    record SKIP "quality script analysis" "scripts/check.sh missing"
    return 0
  fi

  local tool
  for tool in $(collect_quality_tools "${gate}"); do
    if is_declared_in_manifest "${tool}"; then
      record PASS "manifest declares ${tool}" "used by scripts/check.sh"
    else
      record FAIL "manifest declares ${tool}" "scripts/check.sh runs 'uv run ${tool}' but pyproject.toml does not declare it"
      add_blocker "seed manifest BLOCKER: scripts/check.sh가 '${tool}'을 쓰는데 pyproject.toml에 선언이 없다" \
        "pyproject.toml 소유자에게 '${tool}' 선언을 요청하라. uv add나 pip install을 임의로 실행하지 마라."
    fi
  done

  if grep -qE 'uv build' "${gate}"; then
    if grep -qE '^\[build-system\]' "${PROJECT_ROOT}/pyproject.toml"; then
      record PASS "manifest declares build-system" "required by 'uv build' in scripts/check.sh"
    else
      record FAIL "manifest declares build-system" "scripts/check.sh runs 'uv build' but [build-system] is missing"
      add_blocker "seed manifest BLOCKER: uv build를 쓰는데 pyproject.toml에 [build-system]이 없다" \
        "pyproject.toml 소유자에게 [build-system] 선언을 요청하라"
    fi
  fi

  # asyncio_mode = auto는 pytest-asyncio를 필수로 만든다. Textual run_test()가 async라서다.
  if grep -qE '^[[:space:]]*asyncio_mode' "${PROJECT_ROOT}/pyproject.toml"; then
    if is_declared_in_manifest "pytest-asyncio"; then
      record PASS "manifest declares pytest-asyncio" "required by asyncio_mode setting"
    else
      record FAIL "manifest declares pytest-asyncio" "asyncio_mode is set but pytest-asyncio is not declared"
      add_blocker "seed manifest BLOCKER: asyncio_mode 설정이 있는데 pytest-asyncio 선언이 없다" \
        "pyproject.toml 소유자에게 pytest-asyncio 선언을 요청하라"
    fi
  fi

  local runtime_package
  for runtime_package in $(contract_get declared_dependencies.runtime ""); do
    if is_declared_in_manifest "${runtime_package}"; then
      record PASS "manifest declares ${runtime_package}" "runtime dependency"
    else
      record FAIL "manifest declares ${runtime_package}" "contract requires it but pyproject.toml does not declare it"
      add_blocker "seed manifest BLOCKER: runtime dependency '${runtime_package}' 선언이 없다" \
        "pyproject.toml 소유자에게 '${runtime_package}' 선언을 요청하라"
    fi
  done
}

check_lockfile_consistency() {
  if [[ ! -f "${PROJECT_ROOT}/uv.lock" ]]; then
    record FAIL "uv.lock" "missing"
    add_blocker "uv.lock이 없다. uv sync --frozen을 쓸 수 없다." "uv lock"
    return 0
  fi
  if ! command -v uv >/dev/null 2>&1; then
    record SKIP "uv.lock vs pyproject.toml" "uv not installed"
    return 0
  fi

  if run_uv lock --check >"${LOGS_DIR}/uv-lock-check.log" 2>&1; then
    record PASS "uv.lock vs pyproject.toml" "in sync"
  else
    record FAIL "uv.lock vs pyproject.toml" "out of date (see ${ARTIFACTS_SUBDIR}/logs/uv-lock-check.log)"
    add_blocker "pyproject.toml과 uv.lock이 불일치한다" \
      "lockfile 소유자에게 'uv lock' 재생성을 요청하라. preflight는 lockfile을 임의로 바꾸지 않는다."
  fi
}

# ---------------------------------------------------------------------------
# runtime과 package manager
# ---------------------------------------------------------------------------

check_bash_version() {
  if [[ "${BASH_VERSINFO[0]}" -lt 3 ]]; then
    record FAIL "bash version" "${BASH_VERSION} is too old"
    add_blocker "bash 3.2 이상이 필요하다. 현재 ${BASH_VERSION}" "brew install bash"
    return 0
  fi
  record PASS "bash version" "${BASH_VERSION}"
}

check_required_commands() {
  local command_name
  for command_name in $(contract_get required_commands "git bash uv"); do
    if command -v "${command_name}" >/dev/null 2>&1; then
      record PASS "command ${command_name}" "$(command -v "${command_name}")"
    else
      record FAIL "command ${command_name}" "not found in PATH"
      add_user_action "필수 command '${command_name}'이 PATH에 없다" \
        "./scripts/install-prerequisites.sh --provider ${PROVIDER:-claude}"
    fi
  done
}

check_package_manager_version() {
  command -v uv >/dev/null 2>&1 || return 0
  record PASS "uv version" \
    "$(uv --version 2>/dev/null | awk '{print $2}') (min $(contract_get package_manager.min_version 0.5.0))"
}

check_python_runtime() {
  if ! command -v uv >/dev/null 2>&1; then
    record SKIP "python runtime" "uv not installed"
    return 0
  fi

  local logfile="${LOGS_DIR}/python-version.log"
  if ! run_uv run --frozen python -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' >"${logfile}" 2>&1; then
    record WARN "python runtime" "project environment not materialised yet"
    add_install "프로젝트 가상환경이 아직 없다" "uv sync --frozen"
    return 0
  fi

  local detected major minor
  detected="$(tail -1 "${logfile}")"
  major="${detected%%.*}"
  minor="$(printf '%s' "${detected}" | cut -d. -f2)"

  if [[ "${major}" -gt "${MIN_PYTHON_MAJOR}" ]] \
    || { [[ "${major}" -eq "${MIN_PYTHON_MAJOR}" ]] && [[ "${minor}" -ge "${MIN_PYTHON_MINOR}" ]]; }; then
    record PASS "python runtime" "${detected} (min ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR})"
  else
    record FAIL "python runtime" "${detected} < ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}"
    add_blocker "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR} 이상이 필요하다. 감지된 버전 ${detected}" \
      "brew install python@3.12 && uv sync --frozen"
  fi
}

check_inherited_virtualenv() {
  local active="${VIRTUAL_ENV:-}"
  if [[ -z "${active}" ]]; then
    record PASS "inherited VIRTUAL_ENV" "not set"
  elif [[ "${active}" == "${PROJECT_ROOT}/.venv" ]]; then
    record PASS "inherited VIRTUAL_ENV" "matches project .venv"
  else
    record WARN "inherited VIRTUAL_ENV" "${active} differs from project .venv"
    add_warning "셸에 다른 VIRTUAL_ENV가 활성화되어 있다: ${active}" \
      "deactivate   # preflight는 env -u VIRTUAL_ENV로 uv를 호출해 이미 우회한다"
  fi
}

# ---------------------------------------------------------------------------
# 설치 상태
# ---------------------------------------------------------------------------

check_project_executables() {
  local venv_dir="${PROJECT_ROOT}/.venv"
  if [[ ! -d "${venv_dir}" ]]; then
    record WARN "project virtualenv" ".venv missing"
    add_install "프로젝트 .venv가 없다" "uv sync --frozen"
    return 0
  fi

  local missing_count=0 relative_path
  for relative_path in $(contract_get project_executables ""); do
    if [[ -x "${PROJECT_ROOT}/${relative_path}" ]]; then
      record PASS "executable ${relative_path}" ""
    else
      record WARN "executable ${relative_path}" "missing"
      missing_count=$(( missing_count + 1 ))
    fi
  done

  [[ "${missing_count}" -gt 0 ]] || return 0

  # dev group이 빠진 채 sync된 경우와 아예 sync가 안 된 경우를 같은 명령으로 고친다.
  if [[ -x "${venv_dir}/bin/python" ]]; then
    add_install "가상환경은 있으나 executable ${missing_count}개가 없다. dev group이 제외된 채 sync되었을 수 있다." \
      "uv sync --frozen"
  else
    add_install "가상환경이 비어 있다" "uv sync --frozen"
  fi
}

check_required_imports() {
  command -v uv >/dev/null 2>&1 || { record SKIP "python imports" "uv not installed"; return 0; }

  local module_name
  for module_name in $(contract_get required_imports "textual"); do
    if run_uv run --frozen python -c "import ${module_name}" >"${LOGS_DIR}/import-${module_name}.log" 2>&1; then
      record PASS "import ${module_name}" ""
    else
      record WARN "import ${module_name}" "ModuleNotFoundError (declared in pyproject.toml)"
      add_install "'${module_name}' import 실패. 선언은 되어 있으나 설치되지 않았다." "uv sync --frozen"
    fi
  done
}

# ---------------------------------------------------------------------------
# AI engine과 CLIProxyAPI
# ---------------------------------------------------------------------------

read_provider() {
  local provider_file="${PROJECT_ROOT}/.tools/provider"
  if [[ ! -f "${provider_file}" ]]; then
    PROVIDER=""
    record FAIL "provider file" ".tools/provider missing"
    add_user_action "AI provider가 선택되지 않았다" \
      "./scripts/install-prerequisites.sh --provider claude --login"
    return 0
  fi

  PROVIDER="$(tr -d '[:space:]' <"${provider_file}")"
  case "${PROVIDER}" in
    claude|codex|both)
      record PASS "provider file" ".tools/provider = ${PROVIDER}"
      ;;
    skip)
      record WARN "provider file" ".tools/provider = skip"
      add_user_action "provider가 'skip'이다. AI CLI와 provider OAuth가 준비되지 않았다." \
        "./scripts/install-prerequisites.sh --provider claude --login"
      ;;
    *)
      record FAIL "provider file" "invalid value"
      add_blocker ".tools/provider 값이 올바르지 않다: ${PROVIDER}" \
        "./scripts/install-prerequisites.sh --provider claude"
      ;;
  esac
}

check_ralphy_binary() {
  local ralphy_bin="${PROJECT_ROOT}/.tools/bin/ralphy"
  local wrapper="${PROJECT_ROOT}/scripts/ralphy.sh"

  if [[ -x "${wrapper}" ]]; then
    record PASS "ralphy wrapper" "scripts/ralphy.sh"
  else
    record FAIL "ralphy wrapper" "missing or not executable"
    add_blocker "scripts/ralphy.sh를 실행할 수 없다" "chmod +x '${wrapper}'"
  fi

  if [[ ! -x "${ralphy_bin}" ]]; then
    record FAIL "ralphy binary" ".tools/bin/ralphy missing"
    add_user_action "저장소 전용 Ralphy가 설치되지 않았다" \
      "./scripts/install-prerequisites.sh --provider ${PROVIDER:-claude}"
    return 0
  fi

  local reported pinned
  reported="$("${ralphy_bin}" --version 2>/dev/null | tail -1 || true)"
  pinned="$(contract_get ai_engine.ralphy.pinned_version "")"
  record PASS "ralphy binary" "reports '${reported:-unknown}' (pinned ${pinned:-n/a})"

  [[ -n "${pinned}" && -n "${reported}" ]] || return 0
  case "${reported}" in
    *"${pinned}"*) ;;
    *) add_warning "Ralphy가 보고한 버전 '${reported}'이 고정 버전 ${pinned}과 다르게 표시된다" \
         ".tools/ralphy-venv/bin/python -m pip show ralphy" ;;
  esac
}

check_claude_engine() {
  if command -v claude >/dev/null 2>&1; then
    record PASS "claude command" "$(claude --version 2>/dev/null | head -1)"
  else
    record FAIL "claude command" "not found"
    add_user_action "Claude Code CLI가 설치되지 않았다" \
      "./scripts/install-prerequisites.sh --provider claude --login"
  fi

  local env_file
  env_file="$(expand_home "$(contract_get ai_engine.claude.env_file '~/.cli-proxy-api/ralphthon-claude.env')")"
  if [[ ! -f "${env_file}" ]]; then
    record FAIL "claude proxy env file" "missing"
    add_user_action "Claude proxy 환경 파일이 없다" "./scripts/install-prerequisites.sh --provider claude"
    return 0
  fi

  local mode
  mode="$(file_mode "${env_file}")"
  if [[ "${mode}" == "600" ]]; then
    record PASS "claude proxy env file" "present, mode ${mode}"
  else
    record WARN "claude proxy env file" "present, mode ${mode} (expected 600)"
    add_warning "Claude proxy 환경 파일 권한이 느슨하다 (mode ${mode})" "chmod 600 '${env_file}'"
  fi

  # 값은 읽지 않는다. wrapper가 export하는 변수 이름의 존재 여부만 확인한다.
  local variable_name
  for variable_name in $(contract_get ai_engine.claude.required_env_names "ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN"); do
    if grep -qE "^[[:space:]]*export[[:space:]]+${variable_name}=" "${env_file}"; then
      record PASS "env name ${variable_name}" "declared by wrapper source (value not read)"
    else
      record FAIL "env name ${variable_name}" "not declared in proxy env file"
      add_user_action "${variable_name}가 Claude proxy 환경 파일에 없다" \
        "./scripts/install-prerequisites.sh --provider claude"
    fi
  done
}

check_codex_engine() {
  if command -v codex >/dev/null 2>&1; then
    record PASS "codex command" "$(codex --version 2>/dev/null | head -1)"
  else
    record FAIL "codex command" "not found"
    add_user_action "Codex CLI가 설치되지 않았다" \
      "./scripts/install-prerequisites.sh --provider codex --login"
  fi

  local codex_home="${PROJECT_ROOT}/$(contract_get ai_engine.codex.codex_home '.tools/codex-home')"
  local required_file target mode
  for required_file in config.toml auth.json; do
    target="${codex_home}/${required_file}"
    if [[ ! -f "${target}" ]]; then
      record FAIL "codex ${required_file}" "missing"
      add_user_action "프로젝트 전용 CODEX_HOME에 ${required_file}이 없다" \
        "./scripts/install-prerequisites.sh --provider codex"
      continue
    fi
    mode="$(file_mode "${target}")"
    if [[ "${mode}" == "600" ]]; then
      record PASS "codex ${required_file}" "present, mode ${mode} (value not read)"
    else
      record WARN "codex ${required_file}" "present, mode ${mode} (expected 600)"
      add_warning "CODEX_HOME의 ${required_file} 권한이 느슨하다 (mode ${mode})" "chmod 600 '${target}'"
    fi
  done
  record PASS "CODEX_HOME" "wrapper exports project-local ${codex_home}"
}

check_ai_engine() {
  case "${PROVIDER}" in
    claude) check_claude_engine ;;
    codex)  check_codex_engine ;;
    both)
      check_claude_engine
      check_codex_engine
      add_user_action "provider가 'both'다. pilot 명령에 실제 engine을 명시해야 한다." \
        "./scripts/ralph-preflight.sh run ${TASKS_FILE} -- --claude --yaml ${TASKS_FILE} --max-iterations 1 --no-commit"
      ;;
    skip)   record SKIP "ai engine" "provider = skip" ;;
    *)      record SKIP "ai engine" "provider unknown" ;;
  esac
}

check_cliproxyapi() {
  local config_path auth_dir
  config_path="$(expand_home "$(contract_get cliproxyapi.config '~/.cli-proxy-api/config.yaml')")"
  auth_dir="$(expand_home "$(contract_get cliproxyapi.auth_dir '~/.cli-proxy-api')")"

  if command -v cliproxyapi >/dev/null 2>&1; then
    record PASS "cliproxyapi command" "$(command -v cliproxyapi)"
  else
    record FAIL "cliproxyapi command" "not found"
    add_user_action "CLIProxyAPI가 설치되지 않았다" "brew install cliproxyapi"
  fi

  if [[ -d "${auth_dir}" ]]; then
    local dir_mode
    dir_mode="$(file_mode "${auth_dir}")"
    if [[ "${dir_mode}" == "700" ]]; then
      record PASS "cliproxyapi auth dir" "mode ${dir_mode}"
    else
      record WARN "cliproxyapi auth dir" "mode ${dir_mode} (expected 700)"
      add_warning "CLIProxyAPI auth 디렉터리 권한이 느슨하다 (mode ${dir_mode})" "chmod 700 '${auth_dir}'"
    fi
  else
    record FAIL "cliproxyapi auth dir" "missing"
    add_user_action "CLIProxyAPI 설정 디렉터리가 없다" \
      "./scripts/install-prerequisites.sh --provider ${PROVIDER:-claude} --login"
  fi

  if [[ -f "${config_path}" ]]; then
    local config_mode
    config_mode="$(file_mode "${config_path}")"
    if [[ "${config_mode}" == "600" ]]; then
      record PASS "cliproxyapi config" "present, mode ${config_mode} (value not read)"
    else
      record WARN "cliproxyapi config" "present, mode ${config_mode} (expected 600)"
      add_warning "CLIProxyAPI config 권한이 느슨하다 (mode ${config_mode})" "chmod 600 '${config_path}'"
    fi
  else
    record FAIL "cliproxyapi config" "missing"
    add_user_action "CLIProxyAPI config가 없다" "./scripts/install-prerequisites.sh --provider ${PROVIDER:-claude}"
  fi

  check_cliproxyapi_oauth "${auth_dir}" "${config_path}"
  check_cliproxyapi_service
}

# OAuth credential은 auth-dir의 provider별 json이다. 개수만 세고 내용은 읽지 않는다.
check_cliproxyapi_oauth() {
  local auth_dir="$1"
  local config_path="$2"
  [[ -d "${auth_dir}" ]] || return 0

  local credential_count login_flag="--claude-login"
  [[ "${PROVIDER}" == "codex" ]] && login_flag="--codex-login"
  credential_count="$(find "${auth_dir}" -maxdepth 1 -type f -name '*.json' 2>/dev/null | wc -l | tr -d '[:space:]')"

  if [[ "${credential_count}" -gt 0 ]]; then
    record PASS "provider OAuth credential" "${credential_count} credential file(s) present (contents not read)"
    check_credential_permissions "${auth_dir}"
  else
    record FAIL "provider OAuth credential" "no credential file in auth dir"
    add_user_action "provider OAuth가 완료되지 않았다" \
      "cliproxyapi --config '${config_path}' ${login_flag} && brew services restart cliproxyapi"
  fi
}

check_credential_permissions() {
  local auth_dir="$1"
  local credential mode loose=0
  for credential in "${auth_dir}"/*.json; do
    [[ -f "${credential}" ]] || continue
    mode="$(file_mode "${credential}")"
    case "${mode}" in
      600|400) ;;
      *) loose=$(( loose + 1 )) ;;
    esac
  done

  if [[ "${loose}" -eq 0 ]]; then
    record PASS "credential permissions" "all OAuth credential files are owner-only"
  else
    record WARN "credential permissions" "${loose} credential file(s) are group/world readable"
    add_warning "OAuth credential ${loose}개의 권한이 느슨하다. auth 디렉터리가 700이라 노출되진 않지만 조여라." \
      "chmod 600 '${auth_dir}'/*.json"
  fi
}

check_cliproxyapi_service() {
  local listening=false
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${CLIPROXY_PORT}" -sTCP:LISTEN >/dev/null 2>&1 && listening=true
  elif command -v nc >/dev/null 2>&1; then
    nc -z "${CLIPROXY_HOST}" "${CLIPROXY_PORT}" >/dev/null 2>&1 && listening=true
  else
    record SKIP "cliproxyapi listener" "neither lsof nor nc available"
    return 0
  fi

  if [[ "${listening}" == true ]]; then
    record PASS "cliproxyapi listener" "${CLIPROXY_HOST}:${CLIPROXY_PORT} LISTEN"
  else
    record FAIL "cliproxyapi listener" "nothing listening on ${CLIPROXY_HOST}:${CLIPROXY_PORT}"
    add_user_action "CLIProxyAPI가 ${CLIPROXY_HOST}:${CLIPROXY_PORT}에서 실행되고 있지 않다" \
      "brew services restart cliproxyapi"
  fi

  if ! command -v brew >/dev/null 2>&1; then
    record SKIP "cliproxyapi brew service" "brew not available"
    return 0
  fi

  local service_status
  service_status="$(brew services list 2>/dev/null | awk '$1 == "cliproxyapi" {print $2}' | head -1)"
  if [[ "${service_status}" == "started" ]]; then
    record PASS "cliproxyapi brew service" "started"
  elif [[ -n "${service_status}" ]]; then
    record WARN "cliproxyapi brew service" "status '${service_status}'"
    add_user_action "Homebrew service cliproxyapi 상태가 '${service_status}'다" "brew services restart cliproxyapi"
  else
    record WARN "cliproxyapi brew service" "not registered"
    add_user_action "Homebrew service cliproxyapi가 등록되어 있지 않다" "brew services start cliproxyapi"
  fi
}

# ---------------------------------------------------------------------------
# 터미널, locale, git identity
# ---------------------------------------------------------------------------

check_terminal_capability() {
  if [[ -t 1 ]]; then
    record PASS "real TTY" "stdout is a terminal"
    check_terminal_size
  else
    record WARN "real TTY" "not a terminal (headless invocation)"
    add_warning "preflight가 TTY 없이 실행되었다. TUI 실기 확인은 실제 터미널에서 따로 해야 한다." \
      "uv run ralphthon-sample   # 실제 터미널에서"
  fi

  record PASS "headless test path" "uv run pytest는 App.run_test()를 쓰므로 TTY가 필요 없다"
  check_locale
  check_terminal_color
}

check_terminal_size() {
  local size columns lines
  size="$(stty size 2>/dev/null || true)"
  [[ -n "${size}" ]] || return 0

  lines="$(printf '%s' "${size}" | awk '{print $1}')"
  columns="$(printf '%s' "${size}" | awk '{print $2}')"
  if [[ "${columns:-0}" -ge 80 && "${lines:-0}" -ge 24 ]]; then
    record PASS "terminal size" "${columns}x${lines} (min 80x24)"
  else
    record WARN "terminal size" "${columns}x${lines} is smaller than 80x24"
    add_warning "터미널이 80x24보다 작다. 7행 종료 배너 실기 확인이 왜곡된다." "터미널 창을 80x24 이상으로 키워라"
  fi
}

check_locale() {
  local locale_value="${LC_ALL:-${LANG:-}}"
  case "${locale_value}" in
    *UTF-8*|*utf8*|*UTF8*)
      record PASS "UTF-8 locale" "${locale_value}"
      ;;
    "")
      record WARN "UTF-8 locale" "LANG and LC_ALL are unset"
      add_warning "UTF-8 locale이 없다. Textual의 한글과 박스 문자가 깨질 수 있다." "export LANG=en_US.UTF-8"
      ;;
    *)
      record WARN "UTF-8 locale" "${locale_value} is not UTF-8"
      add_warning "locale '${locale_value}'이 UTF-8이 아니다" "export LANG=en_US.UTF-8"
      ;;
  esac
}

check_terminal_color() {
  local term_value="${TERM:-}"
  case "${term_value}" in
    *256color*|*truecolor*|xterm*|screen*|tmux*)
      record PASS "terminal color" "TERM=${term_value}${COLORTERM:+, COLORTERM=${COLORTERM}}"
      ;;
    "")
      record WARN "terminal color" "TERM is unset"
      add_warning "TERM이 설정되지 않았다. 색상 렌더링을 보장할 수 없다." "export TERM=xterm-256color"
      ;;
    *)
      record WARN "terminal color" "TERM=${term_value} may not support 256 colors"
      add_warning "TERM=${term_value}가 256색을 지원하지 않을 수 있다" "export TERM=xterm-256color"
      ;;
  esac
}

check_git_identity() {
  local config_key value missing=false
  for config_key in $(contract_get git.required_config "user.name user.email"); do
    value="$(git -C "${PROJECT_ROOT}" config --get "${config_key}" 2>/dev/null || true)"
    if [[ -n "${value}" ]]; then
      record PASS "git ${config_key}" "configured"
    else
      record FAIL "git ${config_key}" "not configured"
      missing=true
    fi
  done

  [[ "${missing}" == true ]] || return 0
  add_user_action "git identity가 설정되지 않았다. Ralphy의 자동 commit이 실패한다." \
    "git config user.name 'Your Name' && git config user.email 'you@example.com'"
}

check_ralphy_config() {
  local config_path="${PROJECT_ROOT}/.ralphy/config.yaml"
  if [[ ! -f "${config_path}" ]]; then
    record FAIL ".ralphy/config.yaml" "missing"
    add_blocker ".ralphy/config.yaml이 없다" "./scripts/ralphy.sh --init"
    return 0
  fi

  local rule_count
  rule_count="$(awk '/^rules:/{flag=1;next} /^[a-z_]+:/{flag=0} flag && /^- /{count++} END{print count+0}' "${config_path}")"
  record PASS ".ralphy/config.yaml" "${rule_count} rule(s) configured"

  grep -q 'check.sh' "${config_path}" && return 0
  add_warning ".ralphy/config.yaml의 rule에 ./scripts/check.sh 실행이 없다" \
    "./scripts/ralphy.sh --add-rule 'Run ./scripts/check.sh before reporting completion'"
}

check_git_diff_whitespace() {
  if git -C "${PROJECT_ROOT}" diff --check >"${LOGS_DIR}/git-diff-check.log" 2>&1; then
    record PASS "git diff --check" "no whitespace errors"
  else
    record FAIL "git diff --check" "see ${ARTIFACTS_SUBDIR}/logs/git-diff-check.log"
    add_blocker "git diff --check가 공백 오류를 보고했다" "git diff --check"
  fi
}

# ---------------------------------------------------------------------------
# 실행 검증
# ---------------------------------------------------------------------------

check_ralphy_dry_run() {
  local wrapper="${PROJECT_ROOT}/scripts/ralphy.sh"
  if [[ ! -x "${wrapper}" || ! -x "${PROJECT_ROOT}/.tools/bin/ralphy" ]]; then
    record SKIP "ralphy dry-run" "ralphy not available"
    return 0
  fi
  if [[ -z "${PROVIDER}" || "${PROVIDER}" == "skip" ]]; then
    record SKIP "ralphy dry-run" "provider not selected"
    return 0
  fi

  local engine_flag="--claude"
  [[ "${PROVIDER}" == "codex" ]] && engine_flag="--codex"

  local logfile="${LOGS_DIR}/ralphy-dry-run.log"
  local status=0
  run_with_timeout "${RALPHY_DRY_RUN_TIMEOUT}" "${logfile}" \
    run_clean "${wrapper}" "${engine_flag}" --dry-run --yaml "${TASKS_FILE}" --max-iterations 1 --no-commit \
    || status=$?

  if [[ "${status}" -eq 0 ]]; then
    record PASS "ralphy dry-run" "${engine_flag} --dry-run (no task executed)"
  elif [[ "${status}" -eq 143 ]]; then
    record WARN "ralphy dry-run" "timed out after ${RALPHY_DRY_RUN_TIMEOUT}s"
    add_warning "Ralphy dry-run이 ${RALPHY_DRY_RUN_TIMEOUT}초 안에 끝나지 않았다" \
      "./scripts/ralphy.sh ${engine_flag} --dry-run --yaml ${TASKS_FILE}"
  else
    record FAIL "ralphy dry-run" "exit ${status} (see ${ARTIFACTS_SUBDIR}/logs/ralphy-dry-run.log)"
    add_blocker "Ralphy dry-run이 실패했다 (exit ${status})" \
      "./scripts/ralphy.sh ${engine_flag} --dry-run --yaml ${TASKS_FILE} --max-iterations 1 --no-commit"
  fi
}

check_quality_gate() {
  local gate="${PROJECT_ROOT}/scripts/check.sh"
  if [[ ! -x "${gate}" ]]; then
    record SKIP "quality gate" "scripts/check.sh not executable"
    return 0
  fi

  local status=0
  run_with_timeout "${QUALITY_GATE_TIMEOUT}" "${LOGS_DIR}/check-sh.log" run_clean "${gate}" || status=$?

  if [[ "${status}" -eq 0 ]]; then
    record PASS "quality gate" "./scripts/check.sh passed (ruff check, ruff format --check, pytest, uv build)"
  else
    record FAIL "quality gate" "exit ${status} (see ${ARTIFACTS_SUBDIR}/logs/check-sh.log)"
    add_blocker "품질 게이트가 실패했다 (exit ${status})" "./scripts/check.sh"
  fi
}

# ---------------------------------------------------------------------------
# fingerprint와 PASSED marker
# ---------------------------------------------------------------------------

compute_fingerprint() {
  local accumulator="" relative_path
  for relative_path in $(contract_get fingerprint_files ""); do
    accumulator="${accumulator}${relative_path}:$(hash_file "${PROJECT_ROOT}/${relative_path}")"$'\n'
  done
  hash_string "${accumulator}"
}

write_fingerprint() {
  local relative_path
  {
    printf '# ralph preflight environment fingerprint\n'
    printf '# generated %s\n' "$(utc_now)"
    for relative_path in $(contract_get fingerprint_files ""); do
      printf '%s  %s\n' "$(hash_file "${PROJECT_ROOT}/${relative_path}")" "${relative_path}"
    done
    printf 'FINGERPRINT %s\n' "$1"
  } >"${FINGERPRINT_FILE}"
}

read_recorded_fingerprint() {
  [[ -f "${PASSED_FILE}" ]] || return 1
  awk '/^fingerprint:/{print $2; found=1} END{exit !found}' "${PASSED_FILE}"
}

invalidate_stale_pass() {
  [[ -f "${PASSED_FILE}" ]] || return 0

  local recorded current
  recorded="$(read_recorded_fingerprint || true)"
  current="$(compute_fingerprint)"

  [[ -n "${recorded}" && "${recorded}" == "${current}" ]] && return 0
  rm -f "${PASSED_FILE}"
  note "환경 fingerprint가 바뀌어 이전 PASS를 무효화했다."
}

write_passed_marker() {
  local engine="${PROVIDER}"
  [[ "${engine}" == "both" ]] && engine="claude (default; pilot 명령에 명시 필요)"

  {
    printf 'status: PASS\n'
    printf 'verified_at: %s\n' "$(utc_now)"
    printf 'fingerprint: %s\n' "$1"
    printf 'project_root: %s\n' "${PROJECT_ROOT}"
    printf 'tasks_file: %s\n' "${TASKS_FILE}"
    printf 'provider: %s\n' "${PROVIDER:-unset}"
    printf 'engine: %s\n' "${engine:-unset}"
    printf 'uv: %s\n' "$(uv --version 2>/dev/null || printf 'unknown')"
    printf 'bash: %s\n' "${BASH_VERSION}"
    printf 'contract_version: %s\n' "$(contract_get contract_version 0)"
  } >"${PASSED_FILE}"
}

# ---------------------------------------------------------------------------
# 리포트
# ---------------------------------------------------------------------------

overall_status() {
  if [[ "$(count_of BLOCKERS)" -gt 0 ]]; then
    printf 'BLOCKED\n'
  elif [[ "$(count_of INSTALLS)" -gt 0 ]]; then
    printf 'SETUP REQUIRED\n'
  elif [[ "$(count_of USER_ACTIONS)" -gt 0 ]]; then
    printf 'USER ACTION REQUIRED\n'
  else
    printf 'PASS\n'
  fi
}

emit_bucket() {  # emit_bucket <heading> <bucket>
  local total entry index=0
  total="$(count_of "$2")"

  printf '\n### %s\n\n' "$1"
  if [[ "${total}" -eq 0 ]]; then
    printf '없음.\n'
    return 0
  fi

  while [[ "${index}" -lt "${total}" ]]; do
    entry="$(entry_at "$2" "${index}")"
    printf -- '- %s\n' "${entry%%|*}"
    printf -- '  ```bash\n  %s\n  ```\n' "${entry#*|}"
    index=$(( index + 1 ))
  done
}

write_report_rows() {
  local line result rest
  [[ "${#REPORT[@]}" -gt 0 ]] || return 0
  for line in "${REPORT[@]}"; do
    result="${line%%|*}"
    rest="${line#*|}"
    printf '| %s | %s | %s |\n' "${result}" "${rest%%|*}" "${rest#*|}"
  done
}

write_next_command() {
  local status="$1" engine_flag="--claude"
  [[ "${PROVIDER}" == "codex" ]] && engine_flag="--codex"

  printf '\n## 다음 명령\n\n```bash\n'
  if [[ "${status}" == "PASS" ]]; then
    printf './scripts/ralph-preflight.sh run %s -- \\\n' "${TASKS_FILE}"
    printf '  %s \\\n' "${engine_flag}"
    printf '  --yaml %s \\\n' "${TASKS_FILE}"
    printf '  --max-iterations 1 \\\n  --max-retries 1 \\\n  --no-commit\n'
  else
    printf '# 위 조치를 마친 뒤 다시 검증한다\n'
    printf './scripts/ralph-preflight.sh verify %s\n' "${TASKS_FILE}"
  fi
  printf '```\n'
}

write_report() {  # write_report <phase> <status>
  {
    printf '# Ralph preflight report\n\n'
    printf -- '- phase: `%s`\n' "$1"
    printf -- '- status: **%s**\n' "$2"
    printf -- '- generated: %s\n' "$(utc_now)"
    printf -- '- project root: `%s`\n' "${PROJECT_ROOT}"
    printf -- '- tasks file: `%s`\n' "${TASKS_FILE}"
    printf -- '- provider: `%s`\n' "${PROVIDER:-unset}"
    printf -- '- bash: `%s`\n\n' "${BASH_VERSION}"

    printf '## 검사 결과\n\n'
    printf '| 결과 | 항목 | 상세 |\n| --- | --- | --- |\n'
    write_report_rows

    printf '\n## 조치 항목\n'
    emit_bucket 'BLOCKER — setup으로 고칠 수 없다' BLOCKERS
    emit_bucket 'SETUP — ralph-preflight.sh setup 이 처리한다' INSTALLS
    emit_bucket 'USER ACTION — 사용자만 실행할 수 있다' USER_ACTIONS
    emit_bucket 'WARNING — 실행을 막지 않는다' WARNINGS

    write_next_command "$2"
  } >"${REPORT_FILE}"
}

print_summary() {
  printf '\n'
  note "status: $1"
  note "report: ${ARTIFACTS_SUBDIR}/report.md"

  local bucket total entry index
  for bucket in BLOCKERS INSTALLS USER_ACTIONS WARNINGS; do
    total="$(count_of "${bucket}")"
    [[ "${total}" -gt 0 ]] || continue
    printf '\n%s (%s)\n' "${bucket}" "${total}"
    index=0
    while [[ "${index}" -lt "${total}" ]]; do
      entry="$(entry_at "${bucket}" "${index}")"
      printf '  - %s\n    $ %s\n' "${entry%%|*}" "${entry#*|}"
      index=$(( index + 1 ))
    done
  done
}

# sudo가 필요한 작업은 절대 자동 실행하지 않는다. 사용자 검토용 script로 남기기만 한다.
write_privileged_actions() {
  local known
  known="$(contract_get privileged_actions.known '')"

  {
    printf '#!/usr/bin/env bash\n#\n'
    printf '# 사용자 승인이 필요한 권한 작업. preflight는 이 파일을 실행하지 않는다.\n'
    printf '# 내용을 직접 검토한 뒤 필요한 줄만 손으로 실행하라.\n'
    printf '# generated %s\n\nset -Eeuo pipefail\n\n' "$(utc_now)"
    if [[ -z "${known}" ]]; then
      printf '# 현재 감지된 sudo 필요 작업이 없다.\n'
      printf '# Homebrew 설치와 brew services는 일반 사용자 권한으로 동작한다.\n'
      printf 'printf "no privileged action required\\n"\n'
    else
      printf '%s\n' "${known}" | sed 's/^/# /'
    fi
  } >"${PRIVILEGED_FILE}"
  chmod 700 "${PRIVILEGED_FILE}"
}

# ---------------------------------------------------------------------------
# 명령
# ---------------------------------------------------------------------------

run_static_analysis() {
  note "static analysis (no installation, no system change)"
  check_bash_version
  check_git_repository
  check_contract_file
  check_required_files
  check_tasks_file
  check_ralphy_config
  read_provider
  check_required_commands
  check_package_manager_version
  check_inherited_virtualenv
  check_quality_script_dependencies
  check_lockfile_consistency
  check_python_runtime
  check_project_executables
  check_required_imports
  check_ralphy_binary
  check_ai_engine
  check_cliproxyapi
  check_terminal_capability
  check_git_identity
  write_privileged_actions
}

cmd_plan() {
  reset_results
  run_static_analysis

  local status
  status="$(overall_status)"
  write_report "plan" "${status}"
  print_summary "${status}"

  if [[ "$(count_of BLOCKERS)" -gt 0 ]]; then
    printf '\nplan: BLOCKED. BLOCKER를 해결하기 전에는 setup을 실행하지 마라.\n' >&2
    return 1
  fi
  return 0
}

cmd_setup() {
  note "phase: setup (plan first)"
  reset_results
  run_static_analysis

  local status
  status="$(overall_status)"
  write_report "setup:plan" "${status}"

  if [[ "$(count_of BLOCKERS)" -gt 0 ]]; then
    print_summary "${status}"
    printf '\nsetup 중단: BLOCKER가 남아 있다. 설치를 수행하지 않았다.\n' >&2
    return 1
  fi

  if ! command -v uv >/dev/null 2>&1; then
    printf '\nsetup 중단: uv가 없다.\n  $ ./scripts/install-prerequisites.sh --provider %s\n' "${PROVIDER:-claude}" >&2
    return 1
  fi

  note "uv sync --frozen (lockfile 기반 결정적 설치)"
  if ! run_uv sync --frozen >"${LOGS_DIR}/uv-sync.log" 2>&1; then
    cat "${LOGS_DIR}/uv-sync.log" >&2
    printf '\nsetup 실패: uv sync --frozen\n  $ uv sync --frozen\n' >&2
    return 1
  fi
  tail -3 "${LOGS_DIR}/uv-sync.log"
  note "uv sync --frozen 완료"

  note "설치 결과 확인"
  reset_results
  check_project_executables
  check_required_imports

  if [[ "$(count_of INSTALLS)" -gt 0 ]]; then
    print_summary "SETUP INCOMPLETE"
    printf '\nsetup 실패: uv sync 후에도 executable 또는 import가 없다.\n' >&2
    return 1
  fi

  note "setup 완료. 다음: ./scripts/ralph-preflight.sh verify ${TASKS_FILE}"
  return 0
}

cmd_verify() {
  note "phase: verify"
  invalidate_stale_pass
  reset_results

  run_static_analysis
  check_git_diff_whitespace
  check_ralphy_dry_run
  check_quality_gate

  local status
  status="$(overall_status)"
  write_report "verify" "${status}"
  print_summary "${status}"

  if [[ "${status}" != "PASS" ]]; then
    rm -f "${PASSED_FILE}"
    printf '\nverify: %s. PASSED marker를 만들지 않았다.\n' "${status}" >&2
    return 1
  fi

  local fingerprint
  fingerprint="$(compute_fingerprint)"
  write_fingerprint "${fingerprint}"
  write_passed_marker "${fingerprint}"
  note "verify PASS. marker: ${ARTIFACTS_SUBDIR}/PASSED"
  return 0
}

cmd_run() {
  note "phase: run (verify 재수행)"
  if ! cmd_verify; then
    printf '\nrun 중단: verify가 통과하지 않았다. Ralphy를 실행하지 않았다.\n' >&2
    return 1
  fi

  local recorded current
  recorded="$(read_recorded_fingerprint || true)"
  current="$(compute_fingerprint)"
  if [[ -z "${recorded}" || "${recorded}" != "${current}" ]]; then
    printf '\nrun 중단: fingerprint가 최신이 아니다.\n  $ ./scripts/ralph-preflight.sh verify %s\n' "${TASKS_FILE}" >&2
    return 1
  fi

  if [[ "${#PASSTHROUGH[@]}" -eq 0 ]]; then
    printf '\nrun 중단: -- 뒤에 Ralphy option이 없다.\n' >&2
    printf '  $ ./scripts/ralph-preflight.sh run %s -- --claude --yaml %s --max-iterations 1 --max-retries 1 --no-commit\n' \
      "${TASKS_FILE}" "${TASKS_FILE}" >&2
    return 1
  fi

  note "exec scripts/ralphy.sh ${PASSTHROUGH[*]}"
  exec "${PROJECT_ROOT}/scripts/ralphy.sh" "${PASSTHROUGH[@]}"
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

main() {
  local command="${1-}"
  case "${command}" in
    plan|setup|verify|run) shift ;;
    -h|--help)             usage; exit 0 ;;
    "")                    usage >&2; exit 2 ;;
    *)                     usage >&2; die "unknown command: ${command}" ;;
  esac

  bootstrap

  if (($# > 0)) && [[ "$1" != "--" ]]; then
    TASKS_FILE="$1"
    shift
  fi

  PASSTHROUGH=()
  if (($# > 0)); then
    [[ "$1" == "--" ]] || die "unexpected argument '$1'. Ralphy option 앞에 -- 를 넣어라."
    shift
    while (($# > 0)); do
      PASSTHROUGH+=("$1")
      shift
    done
  fi

  # 의도적인 non-zero 종료는 실패가 아니다. ERR trap이 오해를 부르는 줄 번호를 찍지 않도록
  # 상태를 받아 두고 trap을 해제한 뒤 그대로 종료한다.
  local status=0
  case "${command}" in
    plan)   cmd_plan   || status=$? ;;
    setup)  cmd_setup  || status=$? ;;
    verify) cmd_verify || status=$? ;;
    run)    cmd_run    || status=$? ;;
  esac

  trap - ERR
  exit "${status}"
}

main "$@"
