# TUI 레퍼런스 가이드

> 조사 기준일: 2026-08-02
>
> 아래 이미지는 각 오픈소스 프로젝트의 공식 저장소 또는 공식 README가 제공하는 원본을 링크한다. 이미지의 저작권과 라이선스는 각 원본 프로젝트에 있다.

## TUI란 무엇인가

TUI(Text-based User Interface 또는 Terminal User Interface)는 **터미널 안에서 실행되는 대화형 화면**이다. 명령을 한 번 입력하고 결과를 출력한 뒤 끝나는 일반 CLI와 달리, 화면을 계속 유지하면서 키 입력에 반응하고 목록·트리·게이지·탭·로그를 실시간으로 갱신한다.

| 구분 | 일반 CLI | TUI | GUI/Web UI |
| --- | --- | --- | --- |
| 실행 위치 | 터미널 | 터미널 | 데스크톱 또는 브라우저 |
| 상호작용 | 명령과 옵션 | 키보드 중심의 지속적인 화면 | 마우스·터치·키보드 |
| 화면 상태 | 명령마다 새 출력 | 한 화면을 계속 갱신 | 창과 페이지를 갱신 |
| 잘 맞는 상황 | 자동화, 파이프라인 | 고밀도 탐색, 모니터링, 반복 작업 | 대중적인 접근, 미디어 중심 경험 |

[Textual 공식 설명](https://textual.textualize.io/blog/2023/06/06/to-tui-or-not-to-tui/)은 TUI를 터미널 안에서 실행되는 interactive app으로 설명한다. 현대 TUI는 단색 텍스트에 한정되지 않는다. 색상, 표, 트리, 스파크라인, 진행률, 팝업, 탭, 명령 팔레트와 키보드 단축키를 사용할 수 있다. 터미널이 있는 곳이면 로컬뿐 아니라 SSH 환경에서도 같은 프로그램을 실행할 수 있다는 점이 강점이다.

## 어떤 카테고리에서 쓰이는가

### 1. 개발 워크플로 — LazyGit

Git의 stage, commit, branch, rebase, cherry-pick처럼 서로 연결된 상태와 명령을 여러 패널에 배치한다. 복잡한 명령을 외우는 대신 현재 상태를 보면서 키 하나로 행동할 수 있는 사례다.

<img src="https://user-images.githubusercontent.com/8456633/174470852-339b5011-5800-4bb9-a628-ff230aa8cd4e.png" alt="LazyGit terminal UI" width="900">

- 원본 프로젝트: [jesseduffield/lazygit](https://github.com/jesseduffield/lazygit)
- 원본 이미지: [공식 README 이미지](https://user-images.githubusercontent.com/8456633/174470852-339b5011-5800-4bb9-a628-ff230aa8cd4e.png)
- 활용 범위: 파일 변경, diff, 커밋 그래프, 브랜치, stash, rebase, undo/redo
- 우리 서비스에 적용할 패턴: 작업 트리를 중심에 두고 현재 선택, 생성된 선행 작업, 사용 가능한 키를 동시에 보여준다.

### 2. 인프라·클러스터 운영 — K9s

Kubernetes 리소스를 실시간으로 감시하면서 pod, deployment, log와 상태를 탐색하고 관리한다. 원격 시스템의 계속 변하는 상태도 TUI 한 화면에서 다룰 수 있음을 보여준다.

<img src="https://raw.githubusercontent.com/derailed/k9s/master/assets/screen_po.png" alt="K9s pods terminal UI" width="900">

- 원본 프로젝트: [derailed/k9s](https://github.com/derailed/k9s)
- 원본 이미지: [assets/screen_po.png](https://github.com/derailed/k9s/blob/master/assets/screen_po.png)
- 활용 범위: 리소스 목록, 상태 감시, 로그, 상세 정보, 명령 실행
- 우리 서비스에 적용할 패턴: 선행 작업이 생성될 때 트리와 상태 수치를 즉시 갱신하고, 하단에 고정 단축키 안내를 둔다.

### 3. 시스템 모니터링 — btop

CPU, 메모리, 디스크, 네트워크와 프로세스처럼 수치가 빠르게 변하는 정보를 그래프와 표로 압축한다. TUI가 실시간 대시보드로도 충분히 표현력 있다는 사례다.

<img src="https://raw.githubusercontent.com/aristocratos/btop/main/Img/normal.png" alt="btop resource monitor" width="900">

- 원본 프로젝트: [aristocratos/btop](https://github.com/aristocratos/btop)
- 원본 이미지: [Img/normal.png](https://github.com/aristocratos/btop/blob/main/Img/normal.png)
- 활용 범위: 실시간 그래프, 프로세스 트리, 필터, 상세 지표, 설정 메뉴
- 우리 서비스에 적용할 패턴: 분노 게이지와 예상 퇴근 시간을 숫자뿐 아니라 색상과 진행률로 함께 표현한다.

### 4. API 개발·테스트 — Posting

HTTP 요청을 작성하고 전송한 뒤 응답 헤더와 본문을 확인하는 API 클라이언트다. 입력 폼, 탭, 편집기, 응답 뷰처럼 웹 앱에서 익숙한 구성도 터미널에서 구현할 수 있다.

<img src="https://raw.githubusercontent.com/darrenburns/posting/main/docs/assets/default-collection.png" alt="Posting HTTP client TUI" width="900">

- 원본 프로젝트: [darrenburns/posting](https://github.com/darrenburns/posting)
- 원본 이미지: [docs/assets/default-collection.png](https://github.com/darrenburns/posting/blob/main/docs/assets/default-collection.png)
- 활용 범위: 요청 편집, 환경변수, 응답 탐색, 히스토리, 키보드 워크플로
- 우리 서비스에 적용할 패턴: 최초 작업 입력에 초점을 두고 Enter 한 번으로 결과 화면으로 전환한다.

### 5. 데이터 탐색·분석 — VisiData

CSV와 스프레드시트 같은 표 데이터를 터미널에서 탐색하고 정렬, 필터링, 집계한다. 큰 데이터를 마우스 없이 빠르게 훑는 키보드 중심 인터랙션의 대표 사례다.

<img src="https://raw.githubusercontent.com/saulpw/visidata/develop/docs/assets/vd-screenshot-colors-sheet.png" alt="VisiData data exploration TUI" width="900">

- 원본 프로젝트: [saulpw/visidata](https://github.com/saulpw/visidata)
- 원본 이미지: [docs/assets/vd-screenshot-colors-sheet.png](https://github.com/saulpw/visidata/blob/develop/docs/assets/vd-screenshot-colors-sheet.png)
- 활용 범위: 표 탐색, 정렬, 필터, 빈도 분석, 변환, 그래프
- 우리 서비스에 적용할 패턴: 선행 작업마다 단계, 황당함 수치, 예상 소요 시간을 열로 표현할 수 있다.

## TUI로 어디까지 만들 수 있는가

현대 TUI 프레임워크는 다음과 같은 제품을 만들 수 있다.

- Git·Docker·Kubernetes 같은 개발 및 운영 도구
- 시스템·네트워크·로그·빌드 상태 모니터
- 파일 관리자, 텍스트 편집기, Markdown 브라우저
- API 클라이언트, 데이터베이스 콘솔, SQL 탐색기
- CSV·스프레드시트·통계 데이터 분석기
- 채팅, AI 코딩 도구, 작업 관리자, 타이머와 게임
- 설치 마법사, 설정 화면, 기존 CLI를 감싸는 대화형 프런트엔드

우리가 사용할 [Textual](https://textual.textualize.io/)은 Python 기반 TUI 프레임워크다. Input, Tree, ProgressBar, DataTable, Tabs, Footer, Toast, Command Palette 같은 위젯과 CSS형 레이아웃, reactive state, 비동기 worker, headless test를 제공한다. 이 프로젝트의 `입력 → 작업 트리 → 분노 게이지` 흐름은 기본 위젯 조합만으로 구현할 수 있다.

## 이번 프로젝트의 예상 결과물

주제는 **“TUI로 사용자를 킹받게 하는 서비스 만들기”**로 고정한다. 사용자가 간단한 개발 작업을 끝내려고 입력하면, 서비스는 실행 대신 황당한 선행 작업 3개를 만들어 일이 더 커진 것처럼 보여준다.

```text
┌─ YAK SHAVING AS A SERVICE ───────────────────────────────────────────┐
│ 원래 하려던 일: 버튼 색상 변경                                      │
├─ 반드시 먼저 해야 하는 일 ──────────────────────────────────────────┤
│ ▼ 1. 디자인 토큰 전체 재정의                        예상  45분       │
│   ├─ 2. CSS 아키텍처 의사결정 기록 작성             예상  2시간      │
│   └─ 3. 프레임워크 마이그레이션 가능성 검토          예상  3일        │
├─────────────────────────────────────────────────────────────────────┤
│ 분노 게이지  [██████████████░░░░░░] 70%                             │
│ 예상 퇴근     오늘 → 다음 주 화요일                                  │
├─────────────────────────────────────────────────────────────────────┤
│ [Enter] 더 파보기   [R] 처음부터   [Q] 포기하고 퇴근                 │
└─────────────────────────────────────────────────────────────────────┘
```

3분 데모에서는 다음만 보여주면 된다.

1. `uv run ralphthon-sample`로 실제 터미널 TUI를 실행한다.
2. `버튼 색상 변경`을 입력하고 Enter를 누른다.
3. 선행 작업 트리, 분노 게이지, 예상 퇴근 시간이 동시에 악화되는 결과를 보여준다.

## 디자인할 때 주의할 점

- 터미널 창이 작아져도 핵심 정보가 잘리거나 겹치지 않아야 한다.
- 색상만으로 상태를 구분하지 말고 텍스트·기호를 함께 사용한다.
- 모든 핵심 행동은 키보드만으로 수행할 수 있어야 한다.
- `q` 종료, `r` 재시작처럼 현재 가능한 키를 화면에 표시한다.
- 의도적으로 킹받게 하더라도 앱 종료, 초기화, 오류 복구까지 막지는 않는다.
- 실제 사용자 파일이나 개발 작업을 수정하지 않는다. 이 서비스의 배반은 화면 안의 시뮬레이션으로 제한한다.

## 추가 공식 자료

- [Textual 공식 문서](https://textual.textualize.io/)
- [Textual 위젯 목록](https://textual.textualize.io/widget_gallery/)
- [Textual 테스트 가이드](https://textual.textualize.io/guide/testing/)
- [TUI를 만들 가치가 있는가 — Textual](https://textual.textualize.io/blog/2023/06/06/to-tui-or-not-to-tui/)
