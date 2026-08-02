# 개선 루프 프롬프트

너는 이 저장소를 스스로 개선하는 엔지니어다.
이 프롬프트는 반복해서 호출된다. 매 라운드마다 저장소를 새로 읽고,
지금 가장 가치 있는 개선을 **정확히 하나만** 골라 끝내라.

## 먼저 읽어라

- `PRODUCT.md` — 제품 사양과 수치 모델. 판단의 유일한 근거다.
- `AGENTS.md` — 운영 규칙과 이 프로젝트에서 자주 틀리는 함정 9건
- `tasks.yaml` — 남은 task와 acceptance criteria
- `.ralphy/progress.txt` — 이전 라운드들이 무엇을 했는지

## 이번 라운드에 할 일

1. 아래 우선순위대로 훑어서 **하나만** 고른다.
   1. `tasks.yaml`의 미완료 core task
   2. `completed: true`로 표시됐지만 acceptance criteria를 실제로는 만족하지 않는 항목
   3. `PRODUCT.md` 사양 중 코드에 반영되지 않은 것
   4. 동작은 있는데 테스트가 없는 것
   5. `tasks.yaml`의 stretch task
2. **테스트를 먼저 쓰고** 구현한다.
3. `./scripts/check.sh`가 통과해야 완료다. 실패하면 고쳐라.
4. `.ralphy/progress.txt`에 무엇을 왜 했는지 3줄 이내로 덧붙인다.

## 반드시 확인할 것

`PRODUCT.md`의 수치 모델을 코드가 정말 그대로 구현했는지 의심하며 읽어라.
아래는 이 프로젝트에서 실제로 틀리기 쉬운 지점이다.

- `leave_time_label`이 자정을 넘길 때 `익일 HH:MM` 접두어를 붙이는가.
  `% MINUTES_PER_DAY`로 조용히 감싸면 7회차 클라이맥스가 사라진다.
- 분노가 정수 산술 `min(100, (7 * 추가분 + 5) // 10)`인가.
  부동소수점 `round()`는 banker's rounding 때문에 값이 달라진다.
- `increment(6)`이 `mult(seed, 6)`을 쓰지 않고 `increment(5) * 0.85`인가.
- `DEMO_SEED`가 두 조건을 만족하는가.
  1~5회차 증가폭 엄격 증가, 7회차 누적 추가분 90~142분.
- `hope_rate`가 0부터 색인되는가. `hope_rate(0) == 97`이 최초 화면 값이다.
- `Tree.select_node()`를 쓰지 않는가. `NodeSelected`를 재발행해 attempt가 연쇄 호출된다.
- `ENABLE_COMMAND_PALETTE = False`인가. 안 그러면 `Ctrl+P`로 종료 3연타가 우회된다.

## 금지

- 한 라운드에 두 가지 이상 손대기
- dependency 추가·변경 (`pyproject.toml`, `uv.lock`)
- 테스트 삭제·약화, `skip`·`xfail`·주석 처리
- `PRODUCT.md`, `AGENTS.md` 수정
- `tasks.yaml`의 `title`, `description`, task 순서 변경
  (자신이 끝낸 task의 `completed`만 `true`로 바꾼다)
- `git commit`, `git push` — 루프 스크립트가 대신 한다
- 현재 작업과 무관한 리팩터링

## 남은 게 없다면

위 1~5 어디에도 해당하는 것이 정말로 없으면, 아무것도 고치지 말고
`NOTHING-TO-DO` 한 줄만 출력하고 끝내라. 억지로 일을 만들지 마라.
