# Goal Declaration

## One-line Promise
우리는 소프트웨어마에스트로 연수생과 개발자가 터미널에서 간단한 개발 작업을 끝내려는 상황에서 화가 나도록, 작업을 완료할수록 황당한 선행 작업이 늘어나는 야크 셰이빙 TUI를 만든다.

## Demo Scenario
심사 때 3분 안에 보여줄 사용자 흐름:
1. 사용자가 `uv run ralphthon-sample`로 실제 터미널에서 TUI를 실행한다.
2. `버튼 색상 변경` 같은 간단한 개발 작업을 한 줄로 입력하고 Enter를 누른다.
3. 황당한 선행 작업 3개가 트리로 나타나고, 분노 게이지와 예상 퇴근 시간이 함께 상승하는 모습을 확인한다.

## Success Criteria
- [ ] 개발 작업을 입력하고 Enter를 누르면 황당한 선행 작업 3개가 생성된다.
- [ ] 선행 작업 트리, 분노 게이지, 예상 퇴근 시간이 한 화면에서 함께 갱신된다.
- [ ] 모든 핵심 흐름을 키보드만으로 수행할 수 있고 `./scripts/check.sh`가 통과한다.

## Verification Commands
- install: `uv sync --frozen`
- test: `uv run pytest`
- build: `uv build`
- run: `uv run ralphthon-sample`

## AI Autonomy Plan
- 사용할 agent: 설치 시 Claude Code 또는 Codex를 선택한다. 제품 기획과 seed scaffold에는 선택한 CLI를 사용하고, 기능 구현에는 같은 engine의 Ralphy를 사용한다.
- no-touch 구간 동안 agent가 할 일: `PRODUCT.md`, `AGENTS.md`, `tasks.yaml`을 읽고 정확히 한 task만 구현한 뒤 `./scripts/check.sh`를 실행한다. dependency와 기획 문서는 수정하지 않는다.
- 실패 시 agent가 회복하는 방식: 최대 1회 재시도하고, 다시 실패하면 변경사항과 로그를 보존한 채 중단한다. 이후 preflight를 재실행하고 사람이 diff를 검토한다.

## Human Intervention Policy
- 개입 허용 여부: 설치 권한이나 환경 문제 해결, 실패한 파일럿 검토, 최종 커밋 여부 판단에만 허용한다. no-touch 실행 중 제품 코드를 직접 수정하지 않는다.
- 개입 시 기록 방식: 개입 이유, 실행한 명령, 결과를 `.ralphy/preflight/human-interventions.log`에 기록하고 관련 변경은 별도 Git commit으로 남긴다.
