# Ralphy 1시간 TUI 파일럿 프로세스

> 전제: 저장소 루트에 `SETUP_PROMPTS.md`와 `PREFLIGHTS.md`가 있다.
>
> 두 파일은 완성된 프롬프트이므로 내용을 그대로 전달하고 추가 지시를 붙이지 않는다.
> 이번 검증은 1시간 안에 마치기 위해 dry run과 실제 태스크를 각각 최대 1개로 제한한다.

## 1. 제품 기획

```bash
git init
git commit --allow-empty -m "chore: initialize repository"
claude "$(cat SETUP_PROMPTS.md)"
```

대화가 끝나면 `PRODUCT.md`, `AGENTS.md`, `tasks.yaml`을 검토한다. core task가 3~4개이고 stretch task가 1개 이하인지 확인한다.

## 2. Seed scaffold와 Ralphy 초기화

제품 기능을 구현하지 않은 최소 실행 골격만 만든다.

```bash
ralphy \
  --no-commit \
  --max-retries 1 \
  --no-browser \
  "Read PRODUCT.md, tasks.yaml, and AGENTS.md.
Create only the minimal runnable seed project for the fixed stack.
Create a real terminal TUI using Python 3.12+, uv, and Textual.
Create pyproject.toml, uv.lock, a src-layout package, and an executable ./scripts/check.sh.
Add one placeholder TUI screen, one state-logic smoke test, and one headless Textual smoke test using pytest.
The check script must run Ruff lint, Ruff format check, and pytest in that order.
Do not create JavaScript or TypeScript files, a browser UI, web server, or browser test.
Do not implement tasks.yaml, modify planning files, or commit."

ralphy --init
ralphy --add-rule "Before coding, read PRODUCT.md and AGENTS.md"
ralphy --add-rule "Work on exactly one task and avoid unrelated refactoring"
ralphy --add-rule "Run ./scripts/check.sh before reporting completion"
ralphy --add-rule "Do not add, remove, or update dependencies"
ralphy --add-rule "Do not weaken or delete tests"
```

`.ralphy/config.yaml`의 명령과 수정 금지 영역을 확인한다. 최소 금지 대상은 `.env*`, `PRODUCT.md`, `AGENTS.md`, `SETUP_PROMPTS.md`, `PREFLIGHTS.md`다.

## 3. 실행 환경 검증

`PREFLIGHTS.md`만 그대로 실행한다.

```bash
claude -p "$(cat PREFLIGHTS.md)"
```

최종 상태가 `PASS`가 아니면 feature task를 실행하지 않는다.

```bash
bash -n scripts/ralph-preflight.sh
./scripts/ralph-preflight.sh verify tasks.yaml
```

## 4. Seed 확정과 dry run

`.ralphy/preflight/`의 runtime artifact는 Git에서 제외한 뒤 seed를 확정한다.

```bash
git diff --check
git status --short
git add .
git commit -m "chore: create ralph-ready product seed"
git tag product-seed
git switch -c "ralph/session-$(date +%Y%m%d-%H%M)"
git push -u origin HEAD

ralphy \
  --yaml tasks.yaml \
  --dry-run \
  --max-iterations 1 \
  --no-browser \
  --no-commit
```

## 5. 1-task 파일럿 실행

1시간 검증에서는 전체 태스크를 실행하지 않는다. dry run이 통과한 뒤 실제 태스크 하나만 수행하고 결과를 검토한다.

실행 직전에 preflight를 다시 확인한다.

```bash
./scripts/ralph-preflight.sh verify tasks.yaml
```

최종 실행 명령은 다음과 같다.

```bash
ralphy \
  --yaml tasks.yaml \
  --max-iterations 1 \
  --max-retries 1 \
  --no-browser \
  --no-commit
```

이 실행은 기본 sequential mode에서 남은 태스크 중 하나만 처리한다. 자동 커밋은 끄고 사람이 결과를 검토한 뒤 커밋한다.

## 6. 종료 확인과 GitHub 반영

```bash
./scripts/check.sh
git diff --check
git status --short
git log --oneline --decorate product-seed..HEAD
git push
```

파일럿이 통과하면 현재 변경을 검토하고 커밋한다. 이후 같은 명령을 반복하면 `completed: false`인 다음 태스크부터 하나씩 이어서 처리한다.
