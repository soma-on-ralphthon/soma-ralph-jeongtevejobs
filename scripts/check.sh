#!/usr/bin/env bash
#
# 품질 게이트. 완료를 보고하기 전에 반드시 통과해야 한다.
# 실행 항목과 순서는 AGENTS.md에 명시되어 있다. 임의로 바꾸거나 건너뛰지 마라.

set -Eeuo pipefail

readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

run_step() {
  local label="$1"
  shift
  printf '\n==> %s\n' "${label}"
  "$@"
}

run_step 'ruff check' uv run ruff check .
run_step 'ruff format --check' uv run ruff format --check .
run_step 'pytest' uv run pytest
run_step 'uv build' uv build

printf '\nAll checks passed.\n'
