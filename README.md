# ralphthon-sample

> 고정 주제: **TUI로 사용자를 킹받게 하는 서비스 만들기**

소프트웨어마에스트로 연수생이나 개발자가 간단한 개발 작업을 입력하면, 실행하는 대신 황당한 선행 작업이 계속 늘어나는 **야크 셰이빙 TUI**를 만드는 1시간 Ralphy 파일럿 저장소다.

브라우저에서 터미널처럼 보이게 만든 웹 UI가 아니다. Python과 Textual로 실제 터미널 안에서 실행하고 키보드로 조작하는 앱을 만든다.

## 만들 결과물

```text
사용자: 버튼 색상 변경
         │
         ├─ 디자인 토큰 전체 재정의
         ├─ CSS 아키텍처 의사결정 기록 작성
         └─ 프레임워크 마이그레이션 가능성 검토

분노 게이지  [██████████████░░░░░░] 70%
예상 퇴근     오늘 → 다음 주 화요일
```

3분 데모의 핵심 흐름은 다음과 같다.

1. `uv run ralphthon-sample`로 실제 TUI를 실행한다.
2. 간단한 개발 작업을 한 줄 입력하고 Enter를 누른다.
3. 황당한 선행 작업 3개, 분노 게이지, 예상 퇴근 시간이 동시에 나타난다.

자세한 목표와 성공 기준은 [GOAL_DECLARATION.md](GOAL_DECLARATION.md), 원본 양식은 [GOAL_DECLARATION_TEMPLATE.md](GOAL_DECLARATION_TEMPLATE.md)에 있다.

## TUI가 생소하다면

TUI는 터미널 안에서 계속 실행되며 키 입력에 반응하는 대화형 화면이다. 일반 CLI처럼 결과 한 줄을 출력하고 끝나지 않고, 트리·표·탭·게이지·로그를 한 화면에서 실시간으로 갱신할 수 있다.

개발 워크플로, Kubernetes 운영, 시스템 모니터링, API 테스트, 데이터 분석 등 실제 사례와 공식 스크린샷은 [TUI_REFERENCES.md](TUI_REFERENCES.md)에 정리했다.

## 고정 기술 스택

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [Textual](https://textual.textualize.io/)
- pytest / pytest-asyncio
- Ruff
- 로컬 메모리 또는 JSON 상태
- 키보드로 조작하는 실제 TUI

사용하지 않는 것:

- JavaScript, TypeScript, Node.js
- React, Ink, Next.js
- 브라우저 UI, Playwright, 웹 서버
- 외부 유료 API를 사용하는 제품 기능
- 인증, 결제, 배포

## Prerequisites 설치

자동 설치 스크립트는 현재 macOS와 Homebrew를 기준으로 한다. Homebrew가 없다면 먼저 [공식 설치 안내](https://brew.sh/)를 따른다.

OAuth 로그인까지 한 번에 진행하려면:

```bash
./scripts/install-prerequisites.sh --login
```

설치와 로컬 설정만 하고 로그인을 나중에 하려면:

```bash
./scripts/install-prerequisites.sh
```

스크립트가 준비하는 항목:

| 항목 | 설치·검증 방식 | 용도 |
| --- | --- | --- |
| Git | 시스템 command 확인 | 변경 이력과 Ralphy 작업 기준점 |
| Python 3.12+ | 기존 Python 확인, 필요하면 Homebrew | Textual 앱 runtime |
| uv | Homebrew | project dependency와 lockfile 관리 |
| Claude Code | 기존 command 확인, 필요하면 Homebrew stable cask | 기획, seed, Ralphy 기본 AI engine |
| Ralphy | 전용 venv에서 `pip install ralphy==4.0.1` | bounded autonomous task 실행 |
| CLIProxyAPI | Homebrew | Claude/Codex 등의 OAuth provider를 local API로 연결 |

중요: Python 패키지 이름은 `ralphy-cli`가 아니라 **`ralphy`**다. [PyPI 공식 페이지](https://pypi.org/project/ralphy/)의 설치 명령도 `pip install ralphy`이며 Python 3.10+와 Git, AI CLI 하나 이상을 요구한다. 이 저장소는 다른 전역 설치와 충돌하지 않도록 `.tools/ralphy-venv`에 pip 설치하고 `./scripts/ralphy.sh`로 실행한다.

설치 스크립트는 다음 로컬 파일을 만든다.

```text
.tools/bin/ralphy                         # 저장소 전용 PyPI Ralphy
~/.cli-proxy-api/config.yaml             # localhost 전용 proxy 설정
~/.cli-proxy-api/ralphthon.env           # Claude Code 연결 환경변수
```

`.tools/`와 secret·runtime 파일은 Git에 포함하지 않는다.

## CLIProxyAPI 설정

macOS의 공식 설치 방식은 `brew install cliproxyapi`다. 이 저장소의 스크립트는 다음 안전 기본값으로 설정한다.

- `127.0.0.1:8317`에만 bind
- remote management 비활성화
- TLS 비활성화: localhost 안에서만 사용
- 임의의 local API key 생성, 화면에는 출력하지 않음
- `~/.cli-proxy-api/config.yaml`을 Homebrew service config에 연결
- 기존 Homebrew config가 있으면 timestamp가 붙은 `.bak`으로 보존

`--login`을 빼고 설치했다면 Claude OAuth를 직접 시작한다.

```bash
cliproxyapi \
  --config "$HOME/.cli-proxy-api/config.yaml" \
  --claude-login
```

브라우저를 열 수 없는 환경에서는 `--no-browser`를 **CLIProxyAPI 로그인 명령에만** 추가한다. OAuth callback은 로컬 port `54545`를 사용한다.

서비스와 환경변수를 다시 적용한다.

```bash
brew services restart cliproxyapi
source "$HOME/.cli-proxy-api/ralphthon.env"
```

서비스 확인:

```bash
brew services list
lsof -nP -iTCP:8317 -sTCP:LISTEN
```

CLIProxyAPI의 공식 문서:

- [macOS Quick Start](https://help.router-for.me/introduction/quick-start)
- [Basic Configuration](https://help.router-for.me/configuration/basic)
- [Claude OAuth login](https://help.router-for.me/configuration/provider/claude-code)
- [Claude Code client 연결](https://help.router-for.me/agent-client/claude-code)
- [CLIProxyAPI GitHub](https://github.com/router-for-me/CLIProxyAPI)

## 1시간 파일럿 절차

### 1. 제품 기획

먼저 proxy 환경을 현재 shell에 적용한다.

```bash
source "$HOME/.cli-proxy-api/ralphthon.env"
```

완성된 기획 프롬프트만 Claude Code에 전달한다.

```bash
claude "$(cat SETUP_PROMPTS.md)"
```

Claude가 질문을 한 번에 하나씩 한다. 마지막 답변까지 합의한 뒤 정확히 `확정`이라고 입력한다. 그러면 다음 세 파일이 생성된다.

- `PRODUCT.md`
- `AGENTS.md`
- `tasks.yaml`

core task가 3~4개, stretch task가 1개 이하인지 확인한다.

### 2. 최소 seed scaffold

제품 기능을 구현하기 전에 실행 가능한 Python TUI 골격과 테스트만 만든다.

```bash
./scripts/ralphy.sh \
  --no-commit \
  --max-retries 1 \
  "Read PRODUCT.md, tasks.yaml, and AGENTS.md.
Create only the minimal runnable seed project for the fixed stack.
Create a real terminal TUI using Python 3.12+, uv, and Textual.
Create pyproject.toml, uv.lock, a src-layout package, and an executable ./scripts/check.sh.
Add one placeholder TUI screen, one state-logic smoke test, and one headless Textual smoke test using pytest.
The check script must run Ruff lint, Ruff format check, and pytest in that order.
Do not create JavaScript or TypeScript files, a browser UI, web server, or browser test.
Do not implement tasks.yaml, modify planning files, or commit."
```

### 3. Ralphy 초기화와 규칙

```bash
./scripts/ralphy.sh --init
./scripts/ralphy.sh --add-rule "Before coding, read PRODUCT.md and AGENTS.md"
./scripts/ralphy.sh --add-rule "Work on exactly one task and avoid unrelated refactoring"
./scripts/ralphy.sh --add-rule "Run ./scripts/check.sh before reporting completion"
./scripts/ralphy.sh --add-rule "Do not add, remove, or update dependencies"
./scripts/ralphy.sh --add-rule "Do not weaken or delete tests"
```

`.ralphy/config.yaml`에서 test와 lint command, 수정 금지 영역을 확인한다. 최소 금지 대상은 `.env*`, `PRODUCT.md`, `AGENTS.md`, `SETUP_PROMPTS.md`, `PREFLIGHTS.md`, `GOAL_DECLARATION*.md`다.

### 4. Preflight

```bash
claude -p "$(cat PREFLIGHTS.md)"
```

최종 상태가 `PASS`가 아니면 feature task를 실행하지 않는다.

```bash
bash -n scripts/ralph-preflight.sh
./scripts/ralph-preflight.sh verify tasks.yaml
```

### 5. Seed 기준점과 dry run

```bash
git diff --check
git status --short
git add .
git commit -m "chore: create ralph-ready TUI seed"
git tag product-seed
```

PyPI Ralphy 4.0.1이 실제로 지원하는 bounded 옵션만 사용한다. npm판에 있는 `--no-browser`는 PyPI판에 없으므로 Ralphy 명령에 넣지 않는다.

```bash
./scripts/ralphy.sh \
  --yaml tasks.yaml \
  --dry-run \
  --max-iterations 1 \
  --no-commit
```

### 6. 실제 task 하나만 파일럿

```bash
./scripts/ralph-preflight.sh run tasks.yaml -- \
  --yaml tasks.yaml \
  --max-iterations 1 \
  --max-retries 1 \
  --no-commit
```

실행 후 반드시 사람이 확인한다.

```bash
./scripts/check.sh
git diff --check
git status --short
git diff --stat
```

검증이 통과했을 때만 커밋한다. 남은 task는 같은 bounded 명령을 반복해 하나씩 진행한다.

## 파일 안내

| 파일 | 역할 |
| --- | --- |
| `README.md` | 설치부터 1-task 파일럿까지의 단일 실행 안내 |
| `TUI_REFERENCES.md` | TUI 정의, 카테고리별 실제 사례, 공식 이미지 |
| `GOAL_DECLARATION.md` | 이 프로젝트의 데모와 성공 기준 |
| `SETUP_PROMPTS.md` | 제품 기획용 완성 프롬프트 |
| `PREFLIGHTS.md` | Ralphy 실행 환경 검증용 완성 프롬프트 |
| `scripts/install-prerequisites.sh` | Python, uv, Claude Code, PyPI Ralphy, CLIProxyAPI 설치·설정 |
| `scripts/ralphy.sh` | 저장소 전용 PyPI Ralphy 실행 wrapper |

## 공식 근거 링크

- [PyPI Ralphy](https://pypi.org/project/ralphy/)
- [Claude Code 설치](https://code.claude.com/docs/en/quickstart)
- [uv 문서](https://docs.astral.sh/uv/)
- [Textual 문서](https://textual.textualize.io/)
- [CLIProxyAPI Quick Start](https://help.router-for.me/introduction/quick-start)
