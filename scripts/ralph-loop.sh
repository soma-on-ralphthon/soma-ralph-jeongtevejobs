#!/usr/bin/env bash
#
# 무한 개선 루프. LOOP_PROMPT.md 를 반복해서 던지고, 게이트를 통과한 라운드만 커밋한다.
#
#   ./scripts/ralph-loop.sh          # 무제한
#   ./scripts/ralph-loop.sh 5        # 5라운드만
#
#   LOOP_SLEEP=10 ./scripts/ralph-loop.sh      # 라운드 간 대기(기본 5초)
#   LOOP_MAX_FAILS=2 ./scripts/ralph-loop.sh   # 연속 게이트 실패 허용치(기본 3)
#
# 멈추는 법
#   Ctrl+C  또는  touch .ralphy/STOP
#
# push 는 하지 않는다. 사람이 검토 후 직접 push 한다.

set -Eeuo pipefail

if [[ "${EUID}" -eq 0 ]]; then
  printf 'ERROR: root로 실행하지 마라.\n' >&2
  exit 1
fi

PROJECT_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${PROJECT_ROOT}" ]]; then
  PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
readonly PROJECT_ROOT
cd "${PROJECT_ROOT}"

readonly PROMPT_FILE="LOOP_PROMPT.md"
readonly STOP_FILE=".ralphy/STOP"
readonly LOG_DIR=".ralphy/loop-logs"
readonly RALPHY="./scripts/ralphy.sh"
readonly GATE="./scripts/check.sh"

readonly MAX_ROUNDS="${1:-0}"          # 0 = 무제한
readonly SLEEP_SECONDS="${LOOP_SLEEP:-5}"
readonly MAX_CONSECUTIVE_FAILS="${LOOP_MAX_FAILS:-3}"

for required in "${PROMPT_FILE}" "${RALPHY}" "${GATE}"; do
  if [[ ! -e "${required}" ]]; then
    printf 'ERROR: %s 가 없다.\n' "${required}" >&2
    exit 1
  fi
done

mkdir -p "${LOG_DIR}"
rm -f "${STOP_FILE}"

round=0
committed=0
consecutive_fails=0

log() { printf '\n[loop] %s\n' "$1"; }

finish() {
  printf '\n============================================\n'
  printf '루프 종료: %s\n' "$1"
  printf '  라운드: %s\n' "${round}"
  printf '  커밋:   %s\n' "${committed}"
  printf '  로그:   %s/\n' "${LOG_DIR}"
  printf '============================================\n'
  exit "${2:-0}"
}

trap 'finish "사용자 중단(Ctrl+C)" 130' INT TERM

while :; do
  if [[ -f "${STOP_FILE}" ]]; then
    finish "STOP 파일 감지" 0
  fi
  if [[ "${MAX_ROUNDS}" -gt 0 && "${round}" -ge "${MAX_ROUNDS}" ]]; then
    finish "최대 라운드(${MAX_ROUNDS}) 도달" 0
  fi

  round=$((round + 1))
  round_log="${LOG_DIR}/round-${round}.log"
  log "라운드 ${round} 시작 → ${round_log}"

  # -v 는 필수다. 없으면 Claude Code 가
  # 'When using --print, --output-format=stream-json requires --verbose' 로 거부한다.
  set +e
  "${RALPHY}" --claude -v --max-retries 1 --no-commit "$(cat "${PROMPT_FILE}")" 2>&1 \
    | tee "${round_log}"
  ralphy_status="${PIPESTATUS[0]}"
  set -e

  # ralphy 가 시작 배너에 프롬프트 전문을 찍기 때문에, 로그에는 LOOP_PROMPT.md 의
  # "NOTHING-TO-DO" 설명 문장도 들어 있다. 부분 일치로 보면 매 라운드 오탐이 난다.
  # 로그 끝부분에서 정확히 그 한 줄만 있는 경우만 종료로 판정한다.
  if tail -30 "${round_log}" | grep -qx "NOTHING-TO-DO"; then
    finish "에이전트가 더 할 일이 없다고 보고" 0
  fi

  if [[ "${ralphy_status}" -ne 0 ]]; then
    log "ralphy 비정상 종료(exit ${ralphy_status})"
  fi

  log "게이트 실행"
  if "${GATE}" >> "${round_log}" 2>&1; then
    consecutive_fails=0
    if [[ -n "$(git status --porcelain)" ]]; then
      git add -A
      git commit -q -m "loop(${round}): 자동 개선 라운드

LOOP_PROMPT.md 기준 한 라운드. ./scripts/check.sh 통과 후 기록한다.
상세 로그: ${round_log}

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
      committed=$((committed + 1))
      log "게이트 통과 → 커밋 $(git rev-parse --short HEAD)"
    else
      log "게이트 통과했으나 변경 없음"
    fi
  else
    consecutive_fails=$((consecutive_fails + 1))
    log "게이트 실패 (${consecutive_fails}/${MAX_CONSECUTIVE_FAILS}) — 커밋하지 않는다"
    if [[ "${consecutive_fails}" -ge "${MAX_CONSECUTIVE_FAILS}" ]]; then
      finish "게이트 연속 ${MAX_CONSECUTIVE_FAILS}회 실패. 변경사항은 보존한다" 1
    fi
    log "다음 라운드가 이 실패를 고치도록 둔다"
  fi

  sleep "${SLEEP_SECONDS}"
done
