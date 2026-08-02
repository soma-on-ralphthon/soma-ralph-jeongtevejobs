# Ralphthon TUI Starter

Python과 Textual로 TUI 프로젝트를 기획하고, Ralphy를 이용해 제한된 범위의 작업 하나를 자동화해 보는 공용 스타터 저장소다.

브라우저에 터미널 모양을 흉내 낸 웹 UI가 아니라 실제 터미널에서 실행되고 키보드 입력에 반응하는 앱을 대상으로 한다. 구체적인 제품 아이디어와 데모 시나리오는 참여자가 기획 과정에서 결정한다.

## 시작하기

### 1. 사전 준비

macOS와 Homebrew를 기준으로 Python, uv, Ralphy, CLIProxyAPI와 Claude 또는 Codex를 준비한다.

```bash
# 둘 중 하나 선택
./scripts/install-prerequisites.sh --provider claude --login
./scripts/install-prerequisites.sh --provider codex --login
```

OAuth의 대상, 설치 항목, 생성 파일, 수동 로그인, 서비스 확인 방법은 [PREREQUISITES.md](PREREQUISITES.md)에 따로 정리했다.

### 2. TUI 가능성 살펴보기

TUI의 개념과 지도, 프레젠테이션, 노트북, 음악, 게임, 애니메이션 등 창의적인 실제 사례는 [TUI_REFERENCES.md](TUI_REFERENCES.md)를 참고한다.

### 3. 목표 선언

[GOAL_DECLARATION_TEMPLATE.md](GOAL_DECLARATION_TEMPLATE.md)를 복사해 대상 사용자, 데모 흐름, 성공 기준과 검증 명령을 먼저 작성한다. [GOAL_DECLARATION.md](GOAL_DECLARATION.md)는 작성 예시다.

### 4. 제품 기획

설치 때 고른 agent로 [SETUP_PROMPTS.md](SETUP_PROMPTS.md)를 연다.

```bash
# Claude
source "$HOME/.cli-proxy-api/ralphthon-claude.env"
claude "$(cat SETUP_PROMPTS.md)"

# Codex
CODEX_HOME="$PWD/.tools/codex-home" codex "$(cat SETUP_PROMPTS.md)"
```

Agent가 질문을 마치면 `PRODUCT.md`, `AGENTS.md`, `tasks.yaml`을 생성한다. 1시간 안에 끝낼 수 있도록 core task는 3~4개, stretch task는 1개 이하로 제한한다.

### 5. Seed와 preflight

제품 기능보다 먼저 실행 가능한 Python/Textual 골격, headless test와 `scripts/check.sh`를 만든다. 그다음 Ralphy 설정을 초기화한다.

```bash
./scripts/ralphy.sh --init
./scripts/ralphy.sh --add-rule "Before coding, read PRODUCT.md and AGENTS.md"
./scripts/ralphy.sh --add-rule "Work on exactly one task and avoid unrelated refactoring"
./scripts/ralphy.sh --add-rule "Run ./scripts/check.sh before reporting completion"
./scripts/ralphy.sh --add-rule "Do not add, remove, or update dependencies"
./scripts/ralphy.sh --add-rule "Do not weaken or delete tests"
```

선택한 agent에 [PREFLIGHTS.md](PREFLIGHTS.md)를 전달한다. 생성된 preflight의 최종 상태가 `PASS`가 아니면 feature task를 실행하지 않는다.

```bash
# Claude
source "$HOME/.cli-proxy-api/ralphthon-claude.env"
claude -p "$(cat PREFLIGHTS.md)"

# Codex
CODEX_HOME="$PWD/.tools/codex-home" codex exec - < PREFLIGHTS.md
```

### 6. Task 하나만 시험하기

먼저 dry run으로 입력과 범위를 확인한다. Claude를 사용한다면 `--codex`를 `--claude`로 바꾼다.

```bash
./scripts/ralphy.sh \
  --codex \
  --yaml tasks.yaml \
  --dry-run \
  --max-iterations 1 \
  --no-commit
```

Preflight가 통과한 뒤 실제 task도 한 번에 하나만 실행한다.

```bash
./scripts/ralph-preflight.sh run tasks.yaml -- \
  --codex \
  --yaml tasks.yaml \
  --max-iterations 1 \
  --max-retries 1 \
  --no-commit
```

실행 후에는 사람이 검사하고, 검증이 통과한 경우에만 커밋한다.

```bash
./scripts/check.sh
git diff --check
git status --short
git diff --stat
```

## 기본 기술 범위

- Python 3.12+, uv, Textual
- pytest, pytest-asyncio, Ruff
- 실제 터미널과 키보드 중심 인터랙션
- 로컬 메모리 또는 JSON 상태
- JavaScript/TypeScript 제품 코드, 브라우저 UI, 웹 서버, 인증, 결제, 배포 제외

## 문서 안내

| 파일 | 역할 |
| --- | --- |
| `PREREQUISITES.md` | 도구 설치, provider 선택, OAuth와 문제 확인 |
| `TUI_REFERENCES.md` | TUI 개념과 창의적인 실제 사례 |
| `GOAL_DECLARATION_TEMPLATE.md` | 목표 선언 원본 양식 |
| `GOAL_DECLARATION.md` | 작성된 목표 선언 예시 |
| `SETUP_PROMPTS.md` | 제품 기획 prompt |
| `PREFLIGHTS.md` | 실행 환경 검증 prompt |
| `scripts/install-prerequisites.sh` | macOS prerequisite 설치·설정 |
| `scripts/ralphy.sh` | 저장소 전용 Ralphy wrapper |
