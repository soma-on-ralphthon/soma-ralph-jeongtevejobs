# TUI 레퍼런스 가이드

> 조사 기준일: 2026-08-02
>
> 이미지는 각 프로젝트의 공식 저장소가 제공하는 원본을 링크한다. 저작권과 라이선스는 각 원본 프로젝트에 있다.

## TUI란 무엇인가

TUI(Text-based User Interface 또는 Terminal User Interface)는 터미널 안에서 실행되는 대화형 화면이다. 명령을 실행하고 바로 끝나는 일반 CLI와 달리 화면을 유지하면서 키보드나 마우스 입력에 반응하고 상태를 계속 갱신한다.

| 구분 | 일반 CLI | TUI | GUI/Web UI |
| --- | --- | --- | --- |
| 실행 위치 | 터미널 | 터미널 | 데스크톱 또는 브라우저 |
| 상호작용 | 명령과 option | 지속적인 화면과 key binding | 창, page, pointer |
| 상태 표현 | 새 출력이 아래로 쌓임 | 기존 화면을 다시 그림 | component를 다시 그림 |
| 강점 | script와 자동화 | 밀도 높은 탐색, 즉각적인 feedback, SSH | 높은 대중성, 풍부한 media |

[Textual의 TUI 설명](https://textual.textualize.io/blog/2023/06/06/to-tui-or-not-to-tui/)처럼 현대 TUI는 단색 문자에 한정되지 않는다. 24-bit color, Unicode와 Braille 문자, mouse event, inline image protocol, animation, popup, tab, command palette까지 사용할 수 있다.

## 터미널에서 이런 것까지 만들 수 있다

### 1. 세계지도를 탐색하는 캔버스 — MapSCII

MapSCII는 OpenStreetMap vector tile을 Braille과 ASCII 문자로 렌더링한다. 방향키나 mouse drag로 이동하고 zoom하며 주변 장소를 탐색할 수 있다. 터미널의 격자를 단순한 표가 아니라 **공간을 움직이는 canvas**로 사용한 사례다.

<img src="https://cloud.githubusercontent.com/assets/1259904/25480718/497a64e2-2b4a-11e7-9cf0-ed52ee0b89c0.png" alt="MapSCII world map in a terminal" width="900">

- 원본 프로젝트: [rastapasta/mapscii](https://github.com/rastapasta/mapscii)
- 원본 이미지: [공식 README 이미지](https://cloud.githubusercontent.com/assets/1259904/25480718/497a64e2-2b4a-11e7-9cf0-ed52ee0b89c0.png)
- 아이디어 확장: 캠퍼스 탐험, 관계망 항해, 로그를 지형처럼 탐색하기, 선택에 따라 열리는 세계관
- 주목할 표현: Braille 문자의 높은 공간 해상도, pan/zoom, mouse와 keyboard 병행

### 2. 발표와 라이브 코딩 무대 — Presenterm

Presenterm은 Markdown을 터미널 slide deck으로 재생한다. image와 animated GIF, syntax highlight, Mermaid/D2 diagram, LaTeX/Typst 수식, slide transition뿐 아니라 발표 도중 code snippet을 실행하는 기능도 제공한다.

<img src="https://raw.githubusercontent.com/mfontanini/presenterm/master/docs/src/assets/demo.gif" alt="Presenterm terminal slide deck" width="900">

- 원본 프로젝트: [mfontanini/presenterm](https://github.com/mfontanini/presenterm)
- 원본 이미지: [docs/src/assets/demo.gif](https://github.com/mfontanini/presenterm/blob/master/docs/src/assets/demo.gif)
- 아이디어 확장: 선택형 스토리, terminal escape room, live coding quiz, 실행 결과가 다음 장면을 바꾸는 발표
- 주목할 표현: 장면 전환, progressive reveal, speaker note, image와 code의 혼합

### 3. 계산 가능한 문서 — Euporie

Euporie는 Jupyter notebook과 kernel을 터미널 안에서 실행한다. cell 편집과 실행뿐 아니라 Markdown, table, image, LaTeX, HTML, SVG, PDF output과 Jupyter widget도 다룬다. TUI가 dashboard를 넘어 **문서·실험·결과가 연결된 작업 공간**이 될 수 있음을 보여준다.

<img src="https://github.com/joouha/euporie/assets/12154190/c8ea6e23-11bb-4ffc-a9e5-111f788c51ae" alt="Euporie Jupyter notebook in a terminal" width="900">

- 원본 프로젝트: [joouha/euporie](https://github.com/joouha/euporie)
- 원본 이미지: [공식 README gallery 이미지](https://github.com/joouha/euporie/assets/12154190/c8ea6e23-11bb-4ffc-a9e5-111f788c51ae)
- 아이디어 확장: 재현 가능한 실험 일지, 데이터로 진행되는 수사물, 명령을 실행해야 다음 설명이 열리는 tutorial
- 주목할 표현: 편집 가능한 cell, rich output, inline image, 결과를 보존하는 notebook 구조

### 4. 음악 플레이어와 오디오 시각화 — spotify-player

spotify-player는 검색, 재생 queue와 playlist를 터미널에서 조작하고 terminal protocol에 따라 album art도 표시한다. 별도의 audio analysis를 받아 spectrum 형태로 시각화하는 기능도 있다. 소리가 주인공인 제품에서도 TUI가 충분한 controller이자 visual companion이 될 수 있다.

<img src="https://github.com/user-attachments/assets/8c21c1b0-5276-4a9e-b719-e0c2bd555537" alt="spotify-player audio visualization" width="900">

- 원본 프로젝트: [aome510/spotify-player](https://github.com/aome510/spotify-player)
- 원본 이미지: [공식 audio visualization 이미지](https://github.com/user-attachments/assets/8c21c1b0-5276-4a9e-b719-e0c2bd555537)
- 아이디어 확장: 집중도에 반응하는 soundtrack, keyboard DJ, 소리로 상태를 알려주는 timer, text 기반 rhythm interaction
- 주목할 표현: media control, album art, spectrum, 현재 재생 상태의 지속적인 feedback

### 5. SSH 접속 자체가 멀티플레이 입구 — SSHTron

SSHTron은 별도 앱이나 web 회원가입 없이 SSH 접속만으로 여러 사람이 함께 플레이하는 Tron 스타일 game이다. terminal protocol을 UI뿐 아니라 **배포와 접속 방식**으로도 활용한 사례다.

<img src="https://raw.githubusercontent.com/zachlatta/sshtron/master/static/img/gameplay.gif" alt="SSHTron multiplayer terminal game" width="900">

- 원본 프로젝트: [zachlatta/sshtron](https://github.com/zachlatta/sshtron)
- 원본 이미지: [static/img/gameplay.gif](https://github.com/zachlatta/sshtron/blob/master/static/img/gameplay.gif)
- 아이디어 확장: URL 대신 `ssh`로 입장하는 전시, 익명 협동 puzzle, 같은 terminal room에서 진행하는 hackathon game
- 주목할 표현: 실시간 multiplayer state, 낮은 진입 장벽, remote terminal 자체를 distribution channel로 사용

### 6. 파일 목록이 아니라 시각적 탐색 — broot

broot는 거대한 directory tree를 한 화면에 압축하고 fuzzy search, file preview와 작업 명령을 제공한다. 지원 terminal에서는 image도 바로 미리 볼 수 있다. 정보량을 무작정 줄이지 않고 **맥락을 보존한 채 압축**하는 TUI 설계를 참고하기 좋다.

<img src="https://raw.githubusercontent.com/Canop/broot/main/website/src/img/20230930-preview-image.png" alt="broot terminal image preview" width="900">

- 원본 프로젝트: [Canop/broot](https://github.com/Canop/broot)
- 원본 이미지: [website/src/img/20230930-preview-image.png](https://github.com/Canop/broot/blob/main/website/src/img/20230930-preview-image.png)
- 아이디어 확장: 기억을 directory처럼 탐색하기, 선택지가 접히고 펼쳐지는 decision tree, artifact gallery
- 주목할 표현: 정보 압축, fuzzy navigation, context preview, action palette

### 7. 문자를 배우처럼 움직이기 — TerminalTextEffects

TerminalTextEffects는 전통적인 multi-panel TUI보다는 **terminal animation engine에 가까운 인접 사례**다. 글자를 particle처럼 이동시키고 gradient, easing, path, layer와 event를 조합해 불꽃, 번개, Matrix, VHS glitch 같은 효과를 만든다. 상태 변화에 감정과 연출을 더하는 참고 자료로 유용하다.

<img src="https://github.com/user-attachments/assets/7678e1d2-df49-497e-bccd-87b933ece981" alt="TerminalTextEffects thunderstorm animation" width="900">

- 원본 프로젝트: [ChrisBuilds/terminaltexteffects](https://github.com/ChrisBuilds/terminaltexteffects)
- 원본 이미지: [공식 thunderstorm demo](https://github.com/user-attachments/assets/7678e1d2-df49-497e-bccd-87b933ece981)
- 아이디어 확장: 결과에 따라 무너지는 문장, 성공할 때 조립되는 logo, 입력을 삼키는 black hole, terminal ending credit
- 주목할 표현: kinetic typography, easing, particle, scene과 event 기반 animation

## 사례에서 아이디어를 뽑는 방법

기존 GUI를 작게 복제하는 데서 시작하지 않아도 된다. 아래처럼 terminal의 성질 자체를 제품 규칙으로 바꿀 수 있다.

- **접속 방식 활용:** SSH 접속, pipe 입력, command history를 onboarding이나 game rule로 쓴다.
- **문자 격자 활용:** Braille, block, Unicode symbol을 map, waveform, particle, creature로 해석한다.
- **키보드 리듬 활용:** shortcut을 단순 편의 기능이 아니라 combo, 제한 시간, 악기처럼 설계한다.
- **제약 활용:** 작은 화면, 제한된 color, scrollback을 suspense나 단계적 reveal에 사용한다.
- **실시간 상태 활용:** 숫자만 갱신하지 말고 layout, sound, animation, narrative가 함께 반응하게 한다.
- **원격성 활용:** 동일한 app을 local과 SSH에서 실행해 협동, 관전, remote exhibition으로 확장한다.

## 만들 때 확인할 점

- 작은 terminal에서도 핵심 action과 현재 focus가 보여야 한다.
- color만으로 의미를 구분하지 말고 text, symbol과 shape를 병행한다.
- 현재 가능한 key와 종료 방법을 화면에 표시한다.
- resize, `Ctrl+C`, 예외 상황에서 terminal state와 cursor를 복구한다.
- animation은 끄거나 줄일 수 있게 해 접근성과 test 가능성을 확보한다.
- inline image, mouse, true color처럼 terminal마다 다른 기능에는 text fallback을 둔다.
- business logic과 rendering을 분리해 headless test가 가능하게 한다.

## 구현 참고 자료

- [Textual 공식 문서](https://textual.textualize.io/)
- [Textual widget gallery](https://textual.textualize.io/widget_gallery/)
- [Textual animation](https://textual.textualize.io/guide/animation/)
- [Textual testing](https://textual.textualize.io/guide/testing/)
- [Textual의 TUI 설명](https://textual.textualize.io/blog/2023/06/06/to-tui-or-not-to-tui/)
