# Goal Declaration

## One-line Promise
우리는 1줄짜리 작업 지시를 받았지만 실제로는 1줄로 끝나지 않는 경험을 한 개발자가 밤 10시 넘어 마지막 티켓 하나를 끝내려는 상황에서 화가 나도록, 낙관적인 최초 견적으로 헛된 기대를 준 뒤 시도할수록 선행 작업과 예상 퇴근 시간이 조금씩 불어나는 야크 셰이빙 TUI를 만든다.

## Demo Scenario
심사 때 3분 안에 보여줄 사용자 흐름:
1. `uv run ralphthon-sample`로 실제 터미널에서 TUI를 실행하고 `버튼 색상 변경`을 입력한다. `예상 소요 5분`, 퇴근 `22:30`, `성공 확률 97%`가 여유롭게 표시된다.
2. Enter를 일곱 번 누른다. 증가폭이 회차마다 커지다가 6회차에 직전보다 줄어 가짜 안도가 생기고, 사과 문구는 `불편을 드려 죄송합니다`에서 `ㅈㅅ`으로 짧아지다 사라진다. 7회차에 증가폭이 폭증해 퇴근 시간이 자정을 넘어 `익일`로 바뀐다. 분노 86, 성공 확률 21%.
3. `Ctrl+C`로 나가려 한다. **이 첫 키가 8회차 attempt가 되어** 선행 작업 3개가 더 붙고 분노가 100에 도달해 퇴근 시간이 `미정`으로 바뀐다. 종료 배너가 `Ctrl+C 1/3`과 함께 그 전환(`분노 86 → 100`, `누적 +89분`)을 보여준다. 첫 키가 이미 `1/3`이므로 1.5초 안에 두 번 더 눌러야 탈출된다.

증가폭의 정확한 분 단위는 seed에 따라 달라진다. 데모는 검증된 `DEMO_SEED`를 기본값으로 사용하고, 그 seed의 1~8회차 증가폭은 회귀 테스트로 고정한다.

## Success Criteria
- [ ] 작업을 입력하고 Enter를 누르면 황당한 선행 작업 3개가 생성된다.
- [ ] 작업 트리, 분노 게이지, 예상 퇴근 시간이 한 화면에서 하나의 attempt마다 함께 갱신된다.
- [ ] 모든 seed에서 6회차 증가폭이 직전보다 작다.
- [ ] `DEMO_SEED`에서 1~5회차 증가폭이 엄격히 증가하고, 7회차에 퇴근 시간이 `익일`로 바뀌면서 분노는 아직 100 미만이며, 첫 `Ctrl+C`가 만드는 8회차에 분노 100과 `미정`에 도달한다. 그 seed의 1~8회차 증가폭이 회귀 테스트로 고정되어 있다.
- [ ] 분노가 100에 도달하면 예상 퇴근 시간이 `미정`으로 바뀐다.
- [ ] 사과 문구가 회차마다 짧아지고 6회차부터 사라진다.
- [ ] 성공 확률은 최초 화면 97%에서 시작해 attempt마다 감소하고 9회차 이상은 0%다.
- [ ] 첫 `Ctrl+C`/`Ctrl+Q`는 해당 종료 시퀀스에서 정확히 한 번 attempt를 발생시키고 배너를 표시하며, 첫 키를 포함한 세 입력이 1.5초 안에 들어와야 종료된다.
- [ ] 모든 핵심 흐름을 키보드만으로 수행할 수 있고 `./scripts/check.sh`가 통과한다.

## Verification Commands
- install: `uv sync --frozen`
- test: `uv run pytest`
- build: `uv build`
- check: `./scripts/check.sh` (ruff check → ruff format --check → pytest → uv build)
- run: `uv run ralphthon-sample`

## AI Autonomy Plan
- 사용할 agent: 설치 시 Claude Code 또는 Codex를 선택한다. 제품 기획과 seed scaffold에는 선택한 CLI를 사용하고, 기능 구현에는 같은 engine의 Ralphy를 사용한다.
- no-touch 구간 동안 agent가 할 일: `PRODUCT.md`, `AGENTS.md`, `tasks.yaml`을 읽고 가장 위의 미완료 task 하나만 구현한 뒤 `./scripts/check.sh`를 실행한다. dependency와 기획 문서는 수정하지 않고, 완료한 task의 `completed`만 `true`로 바꾼다.
- 실패 시 agent가 회복하는 방식: 최대 1회 재시도하고, 다시 실패하면 변경사항과 로그를 보존한 채 중단한다. 이후 preflight를 재실행하고 사람이 diff를 검토한다. 타임박스를 넘긴 task는 중단하고 무엇을 왜 못 끝냈는지 남긴다.

## Human Intervention Policy
- 개입 허용 여부: 설치 권한이나 환경 문제 해결, 실패한 파일럿 검토, 최종 커밋 여부 판단, 그리고 headless로 확정할 수 없는 실기 검증(`textual keys`로 `Ctrl+Q` 전달 확인, 배너 표시 중 priority binding 순서, 80×24 터미널의 배너 말줄임 — 콘텐츠 6행 + 하단 border로 전체 높이 7행)에만 허용한다. no-touch 실행 중 제품 코드를 직접 수정하지 않는다.
- 개입 시 기록 방식: 개입 이유, 실행한 명령, 결과를 `.ralphy/preflight/human-interventions.log`에 기록하고 관련 변경은 별도 Git commit으로 남긴다.
