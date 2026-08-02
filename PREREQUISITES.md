# Prerequisites 설치 가이드

이 문서는 Ralphthon TUI Starter를 실행하기 위한 도구, Claude/Codex 선택, CLIProxyAPI OAuth와 로컬 설정을 설명한다.

## 지원 환경

자동 설치 스크립트는 현재 다음 환경을 지원한다.

- macOS
- Homebrew
- 일반 사용자 계정: root 또는 전체 script의 `sudo` 실행 금지
- Git이 설치된 저장소

Homebrew가 없다면 [공식 설치 안내](https://brew.sh/)를 먼저 따른다. Linux와 Windows에서는 아래 공식 링크를 참고해 같은 도구를 수동으로 준비해야 한다.

## 빠른 설치

사용할 AI provider를 하나 선택한다.

```bash
# Claude Code 설치·설정 후 Claude 계정 OAuth
./scripts/install-prerequisites.sh --provider claude --login

# Codex CLI 설치·설정 후 ChatGPT/Codex 계정 OAuth
./scripts/install-prerequisites.sh --provider codex --login
```

추가 선택지:

```bash
# 두 CLI와 두 provider OAuth를 모두 준비
./scripts/install-prerequisites.sh --provider both --login

# 설치와 설정만 하고 OAuth는 나중에 진행
./scripts/install-prerequisites.sh --provider claude
./scripts/install-prerequisites.sh --provider codex

# AI CLI 설치와 OAuth를 생략
./scripts/install-prerequisites.sh --provider skip
```

`--login`을 붙였을 때만 브라우저가 열린다. `both`를 선택하면 Claude와 Codex OAuth를 차례로 진행하며, Ralphy wrapper의 기본 engine은 Claude다.

## OAuth는 무엇에 대한 로그인인가

이 OAuth는 만들 TUI의 사용자 인증이나 GitHub 로그인이 아니다. 로컬의 CLIProxyAPI가 사용자의 Claude Code 계정 또는 ChatGPT/Codex 계정을 모델 provider로 사용할 수 있도록 권한을 받는 과정이다.

```text
Ralphy → Claude Code 또는 Codex CLI → localhost CLIProxyAPI → 선택한 모델 계정
```

각 참여자는 자기 계정으로 직접 로그인해야 한다. OAuth credential과 local API key는 Git으로 공유하지 않는다.

- Claude: `cliproxyapi --claude-login`, callback port `54545`
- Codex: `cliproxyapi --codex-login`, callback port `1455`
- 브라우저를 직접 열 수 없으면 로그인 명령에 `--no-browser` 추가

공식 설명은 [Claude OAuth](https://help.router-for.me/configuration/provider/claude-code)와 [Codex OAuth](https://help.router-for.me/configuration/provider/codex)를 참고한다.

## 설치되는 항목

| 항목 | 설치·검증 방식 | 용도 |
| --- | --- | --- |
| Git | 기존 command 확인 | 변경 이력과 Ralphy 기준점 |
| Python 3.12+ | 기존 버전 확인, 필요하면 Homebrew | TUI runtime |
| uv | Homebrew | dependency와 lockfile 관리 |
| Claude Code | `--provider claude|both`일 때 Homebrew cask | 선택 가능한 AI engine |
| Codex CLI | `--provider codex|both`일 때 Homebrew cask | 선택 가능한 AI engine |
| Ralphy | 전용 venv에 `pip install ralphy==4.0.1` | 범위가 제한된 agent task 실행 |
| CLIProxyAPI | Homebrew | provider OAuth를 localhost API로 연결 |

Python 패키지 이름은 `ralphy-cli`가 아니라 **`ralphy`**다. [PyPI Ralphy](https://pypi.org/project/ralphy/)는 `pip install ralphy`를 안내하며 Python 3.10+, Git과 AI CLI 하나 이상을 요구한다. 이 저장소는 전역 환경과 충돌하지 않도록 `.tools/ralphy-venv`에 설치한다.

## 생성되는 로컬 파일

```text
.tools/bin/ralphy                         # 저장소 전용 Ralphy
.tools/provider                          # 선택한 기본 engine
.tools/codex-home/config.toml            # 프로젝트 전용 Codex proxy 설정
.tools/codex-home/auth.json              # local proxy key
~/.cli-proxy-api/config.yaml             # localhost proxy 설정
~/.cli-proxy-api/ralphthon-claude.env    # Claude proxy 환경변수
```

`.tools/`와 credential은 `.gitignore` 대상이다. Codex는 프로젝트 전용 `CODEX_HOME`을 사용하므로 기존 `~/.codex/config.toml`을 덮어쓰지 않는다.

CLIProxyAPI 설정의 안전 기본값:

- `127.0.0.1:8317`에만 bind
- remote management 비활성화
- localhost 내부에서만 사용하므로 TLS 비활성화
- 임의의 local API key를 생성하되 화면에는 출력하지 않음
- 기존 Homebrew config는 timestamp가 붙은 backup으로 보존

## OAuth를 나중에 실행하기

```bash
# Claude
cliproxyapi \
  --config "$HOME/.cli-proxy-api/config.yaml" \
  --claude-login

# Codex
cliproxyapi \
  --config "$HOME/.cli-proxy-api/config.yaml" \
  --codex-login

brew services restart cliproxyapi
```

## 설치 확인

```bash
python3 --version
uv --version
./scripts/ralphy.sh --version
brew services list
lsof -nP -iTCP:8317 -sTCP:LISTEN
```

선택한 engine도 확인한다.

```bash
claude --version
codex --version
```

`scripts/ralphy.sh`는 `--claude`를 받으면 Claude proxy 환경변수를, `--codex`를 받으면 프로젝트 전용 `CODEX_HOME`을 자동 적용한다. 두 flag를 동시에 주면 실행을 거부한다.

## 다른 사람이 저장소를 사용할 때

1. 저장소가 private이면 GitHub 접근 권한을 받는다.
2. 저장소를 clone한다.
3. 자기 provider를 골라 설치 script를 실행한다.
4. 열린 브라우저에서 자기 계정으로 OAuth를 완료한다.
5. credential이나 다른 사람의 `.tools/`를 복사하지 않는다.
6. [README.md](README.md)의 기획과 preflight 순서를 따른다.

설치 script는 반복 실행할 수 있다. provider를 바꾸고 싶다면 원하는 `--provider` 값으로 다시 실행한다.

## 공식 자료

- [Homebrew](https://brew.sh/)
- [Python](https://www.python.org/)
- [uv](https://docs.astral.sh/uv/)
- [PyPI Ralphy](https://pypi.org/project/ralphy/)
- [Claude Code 설치](https://code.claude.com/docs/en/quickstart)
- [Codex CLI 설치](https://learn.chatgpt.com/docs/codex/cli)
- [CLIProxyAPI Quick Start](https://help.router-for.me/introduction/quick-start)
- [CLIProxyAPI Basic Configuration](https://help.router-for.me/configuration/basic)
- [Claude Code client 연결](https://help.router-for.me/agent-client/claude-code)
- [Codex client 연결](https://help.router-for.me/agent-client/codex)
