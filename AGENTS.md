# AGENTS

이 저장소에서 작업하는 에이전트를 위한 운영 지침이다.

코딩을 시작하기 전에 [PRODUCT.md](PRODUCT.md)와 이 문서를 읽어라.
수치 모델과 문구 규칙의 유일한 근거는 PRODUCT.md다. 임의로 바꾸지 마라.

## 프로젝트 명령

| 명령 | 용도 |
| --- | --- |
| `uv sync` | 의존성 동기화 |
| `uv run ralphthon-sample` | 실제 터미널에서 TUI 실행 |
| `uv run pytest` | 전체 테스트 |
| `uv run ruff check .` | 린트 |
| `uv run ruff format --check .` | 포맷 검사 |
| `uv build` | 패키지 빌드 |
| `./scripts/check.sh` | 아래 4개를 묶은 게이트. **완료 보고 전에 반드시 실행한다** |

`./scripts/check.sh`는 최소한 다음을 순서대로 실행하고, 하나라도 실패하면 non-zero로 종료한다.

```
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build
```

`uv sync --frozen`을 쓰려면 no-touch 시작 전에 `uv.lock`이 존재해야 한다. preflight에서 확인한다.

## 디렉터리 구조

`src/ralphthon_sample/app.py`를 진입점으로 하는 src layout이다.

```
src/ralphthon_sample/
  __init__.py
  app.py            진입점. Textual App, 화면 구성, 키 바인딩
  config.py         상수 전용. 매직 넘버를 코드에 박지 마라
  state.py          YakState와 순수 파생 함수. Textual을 import하지 않는다
  texts.py          선행 작업 템플릿, 사과 문구, 성공 확률
  widgets/
    quit_banner.py  종료 배너 ModalScreen
tests/
  test_state.py     순수 함수 단위 테스트
  test_app.py       run_test() headless 테스트
scripts/
  check.sh          품질 게이트
```

## 렌더링과 상태 로직 분리

**`state.py`는 Textual을 import하지 않는다.** 이게 깨지면 상태 로직을 단위 테스트할 수 없다.

- 상태는 `(root_task, attempt_count, seed, started_at)` 네 필드뿐이다.
- 증가폭, 누적 견적, 분노, 퇴근 시간 표기, 사과 문구, 성공 확률은 **전부 순수 파생 함수**다.
  `(seed, attempt_count)`만으로 계산되어야 한다.
- **RNG 객체를 상태로 들고 있지 마라.** 매번 `random.Random(f"{seed}:{n}")`을 새로 만든다.
  RNG를 들고 소비하면 순수 함수가 아니게 되고 회귀 테스트가 재현되지 않는다.
- **상태를 변형하지 마라.** `attempt()`는 새 `YakState`를 반환한다.
- `app.py`는 파생 함수를 호출해 위젯에 반영하기만 한다. 계산 로직을 넣지 마라.

## 키보드 전용

모든 핵심 행동을 실제 터미널에서 키보드만으로 수행할 수 있어야 한다.

- 마우스 클릭이 필요한 인터랙션을 만들지 마라.
- 브라우저에서 터미널을 흉내 내는 UI가 아니다. 실제 TUI다.
- `q` 키를 전역 바인딩으로 만들지 마라. Input에 문자 `q`를 입력할 수 없게 된다.

## 수정 금지 영역

아래는 읽기 전용이다. 어떤 이유로도 수정하지 마라.

- `SETUP_PROMPTS.md`, `PREFLIGHTS.md`, `PREREQUISITES.md`, `README.md`, `TUI_REFERENCES.md`
- `GOAL_DECLARATION.md`, `GOAL_DECLARATION_TEMPLATE.md`
- `PRODUCT.md`, `AGENTS.md`
- `scripts/` 전체
- `.tools/` 전체
- `tasks.yaml` — 단 하나의 예외는 자신이 완료한 task의 `completed` 값이다.
  `title`, `description`, task 순서, task 추가·삭제는 금지다.

## 한 번에 한 task만

- `tasks.yaml`의 **가장 위에 있는 미완료 task 하나만** 수행한다.
- 다음 task를 미리 건드리지 마라.
- 현재 task와 무관한 리팩터링을 하지 마라. 눈에 거슬리는 코드를 발견해도 그대로 둔다.
- task를 끝내면 그 task의 `completed`를 `true`로 바꾸고 멈춘다.

## dependency 임의 추가 금지

- `pyproject.toml`과 `uv.lock`에 패키지를 추가·제거·변경하지 마라.
- 허용된 스택은 Python 3.12+, uv, Textual, pytest, pytest-asyncio, Ruff뿐이다.
- 표준 라이브러리로 해결되지 않으면 그 task를 중단하고 사람에게 보고한다.
- 다음은 금지다 — JavaScript / TypeScript / Node.js, React·Ink·Next.js와 브라우저 UI,
  Playwright와 브라우저 테스트, 웹 서버와 HTTP API, 외부 유료 API, 인증, 결제, 배포.

## 완료 전에 `./scripts/check.sh` 실행

완료를 보고하기 전에 반드시 실행하고 통과를 확인한다.

```bash
./scripts/check.sh
```

실패하면 완료가 아니다. 고치고 다시 실행한다.
실패를 두 번 반복하면 변경사항과 로그를 보존한 채 중단하고 사람에게 넘긴다.

## 테스트를 삭제하거나 약화하지 않는다

- 기존 테스트를 지우지 마라.
- 단언을 느슨하게 바꾸지 마라. `assert x == 3`을 `assert x >= 0`으로 바꾸는 것은 위반이다.
- `skip`, `xfail`, 주석 처리로 실패를 숨기지 마라.
- 테스트가 실패하면 **구현을 고쳐라.** 테스트가 명백히 잘못된 경우에만 테스트를 고치고,
  그때는 왜 잘못됐는지를 커밋 메시지에 남긴다.
- 새 기능에는 새 테스트를 추가한다.

## 이 프로젝트에서 자주 틀리는 것

구현 전에 확인해라. 전부 사전 검증에서 실제로 문제로 지목된 항목이다.

- **`Tree.select_node()`를 쓰지 마라.** `NodeSelected`를 다시 발행해서 `attempt()`가 연쇄 호출된다.
  `move_cursor()` + `scroll_to_node(animate=False)`를 써라.
- **`ENABLE_COMMAND_PALETTE = False`를 빼먹지 마라.**
  `Ctrl+P` 명령 팔레트의 Quit으로 종료 3연타가 우회된다.
- **`inherit_bindings=False`를 쓰지 마라.** 필요 이상으로 넓다.
  `Ctrl+C`와 `Ctrl+Q`만 개별 override한다.
- **`time.monotonic`을 전역 monkeypatch하지 마라.** Textual timer와 Toast가 오염된다.
  App에 clock을 주입하고 테스트에서 교체해라.
- **`run_test()`의 `notifications` 기본값은 `False`다.**
  Toast DOM을 단언하지 말고 `apology_for()` 순수 함수와 `notify()` 호출 spy로 테스트해라.
  private `_notifications`를 단언하지 마라.
- **분노는 정수 산술이다.** `min(100, (7 * 추가분 + 5) // 10)`.
  부동소수점 `round()`는 banker's rounding 때문에 추가분 15·35·55·75·95·115·135에서 다른 값을 낸다.
- **종료 3연타의 세 번째 키에서 `attempt()`를 부르지 마라.**
  마지막 갱신이 repaint 전에 종료되어 화면에 보이지 않는다. 첫 키에서만 1회 호출한다.
- **`hope_rate`는 0부터 색인한다.** `hope_rate(0) = 97`이 최초 화면 값이다.
  1부터 색인하면 아직 시도하지 않은 화면에 표시할 값이 없어진다.
- **임의 seed에 증가폭 단조 증가를 요구하지 마라.** 노이즈 때문에 6회차 외에도 하락할 수 있다.
  단조 증가는 `DEMO_SEED`에서만 보장한다. 6회차 하락만 전체 seed에서 보장된다.

## 막혔을 때

- 최대 1회 재시도한다.
- 다시 실패하면 변경사항과 로그를 보존한 채 중단한다.
- 기획 문서를 고쳐서 문제를 없애려 하지 마라. `PRODUCT.md`와 `tasks.yaml`은 수정 금지다.
- 타임박스를 넘기면 그 task를 중단하고 무엇을 왜 못 끝냈는지 남긴다.
  `tasks.yaml`의 core 3은 20분 안에 배너 표시와 3연타 headless 테스트가 나오지 않으면 중단한다.
