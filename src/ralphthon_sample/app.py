"""ralphthon-sample 진입점.

Textual App, 화면 구성, 키 바인딩만 담당한다.
계산은 전부 state.py 와 texts.py 의 순수 함수에 있다. 여기에 수치 로직을 넣지 마라.
"""

import time
from collections.abc import Callable
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import Footer, Header, Input, ProgressBar, Static, Tree
from textual.widgets.tree import TreeNode

from ralphthon_sample.config import (
    ANGER_MAX,
    APOLOGY_TIMEOUT_SEC,
    DEMO_SEED,
    INITIAL_ESTIMATE_MIN,
    PREREQ_COUNT,
    QUIT_SEQUENCE_LENGTH,
    QUIT_WINDOW_SEC,
    TICK_INTERVAL_SEC,
    TREE_GUIDE_DEPTH,
)
from ralphthon_sample.persistence import default_state_path, load_state, save_state
from ralphthon_sample.state import (
    SECONDS_PER_MINUTE,
    YakState,
    anger,
    increment,
    leave_label,
    leave_time_label,
    next_quit_press,
    remaining_label,
    remaining_seconds,
)
from ralphthon_sample.texts import BLOCKED_LABEL, apology_for, hope_line, prerequisites_for
from ralphthon_sample.widgets.quit_banner import QuitBanner

PLACEHOLDER_TEXT = "오늘 처리할 작업을 한 줄로 입력하고 Enter"
EMPTY_TREE_LABEL = "아직 등록된 작업이 없습니다"
INITIAL_ANGER = 0
INITIAL_ATTEMPT_COUNT = 0
NO_QUIT_SEQUENCE = 0
NO_ADDED_MINUTES = 0
NO_ELAPSED_SECONDS = 0.0


class RalphthonApp(App[None]):
    """야크 셰이빙 TUI.

    좌측 트리 2fr, 우측 상태 패널 1fr, 하단 입력창을 한 화면에 둔다.
    """

    TITLE = "ralphthon-sample"

    # Ctrl+P 명령 팔레트의 Quit 이 살아 있으면 종료 3연타를 통째로 우회할 수 있다.
    ENABLE_COMMAND_PALETTE = False

    # 기본 바인딩 상속은 유지한다. 종료로 이어지는 두 키만 개별 override 한다.
    # inherit_bindings=False 는 필요 이상으로 넓고, q 는 Input 에 문자 q 를 못 넣게 만든다.
    BINDINGS = [
        Binding("ctrl+c", "yak_quit('Ctrl+C')", "종료 시도", priority=True),
        Binding("ctrl+q", "yak_quit('Ctrl+Q')", "종료 시도", priority=True),
    ]

    CSS = """
    #panels {
        height: 1fr;
    }

    #task-tree {
        width: 2fr;
        border: round $secondary;
        padding: 0 1;
    }

    #status {
        width: 1fr;
        border: round $secondary;
        padding: 1 2;
    }

    #status Static {
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        seed: str = DEMO_SEED,
        clock: Callable[[], float] = time.monotonic,
        quit_window: float = QUIT_WINDOW_SEC,
        state_path: Path | None = None,
        tick_interval: float = TICK_INTERVAL_SEC,
    ) -> None:
        super().__init__()
        self._seed = seed
        self.state: YakState | None = None

        # 상태 스냅샷 경로. 테스트는 임시 디렉터리를 주입한다.
        self._state_path = default_state_path() if state_path is None else state_path

        # 종료 시간창과 남은 시간은 같은 주입 clock 으로 잰다.
        # time.monotonic 을 전역 monkeypatch 하면 Textual timer 와 Toast 가 오염된다.
        self._clock = clock
        self._quit_window = quit_window

        # 남은 시간의 기준점. YakState.started_at 이 아니라 주입 clock 으로 잡는다.
        # started_at 은 벽시계 datetime 이고 주입 clock 은 monotonic float 이라 단위가 섞인다.
        # 종료 시간창이 이미 monotonic 을 쓰므로 시각 축을 그쪽으로 통일했다.
        self._tick_interval = tick_interval
        self._elapsed_origin = clock()
        self._quit_presses = NO_QUIT_SEQUENCE
        self._quit_last_at: float | None = None
        self._quit_banner: QuitBanner | None = None
        self._quit_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="panels"):
            yield Tree(EMPTY_TREE_LABEL, id="task-tree")
            with Vertical(id="status"):
                yield Static("분노 게이지", id="anger-label")
                yield ProgressBar(total=ANGER_MAX, show_eta=False, id="anger")
                yield Static(
                    f"예상 소요 {remaining_label(INITIAL_ESTIMATE_MIN * SECONDS_PER_MINUTE)}",
                    id="estimate",
                )
                yield Static(
                    f"예상 퇴근 {leave_time_label(INITIAL_ESTIMATE_MIN)}",
                    id="leave-time",
                )
                yield Static(BLOCKED_LABEL, id="blocked")
                yield Static(hope_line(INITIAL_ATTEMPT_COUNT), id="hope")
        yield Input(placeholder=PLACEHOLDER_TEXT, id="task-input")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#task-tree", Tree).guide_depth = TREE_GUIDE_DEPTH
        self.query_one("#anger", ProgressBar).update(progress=INITIAL_ANGER)
        self.query_one("#task-input", Input).focus()
        self._reset_elapsed_origin()
        self._restore_session()

        # 남은 시간만 1초마다 다시 그린다. 분노·사과·성공 확률은 attempt 가 구동한다.
        self.set_interval(self._tick_interval, self._tick)

    # --- 입력 경로 ------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """입력창 Enter. 최초 등록만 작업을 세우고, 그 뒤로는 무엇을 적든 활성 작업 재시도다."""
        task = event.value.strip()
        event.input.value = ""

        if self.state is not None:
            # 등록이 끝나면 입력 내용은 결과를 바꾸지 않는다. 빈 Enter 와 똑같은 attempt 다.
            # 다른 작업을 적었다고 루트를 갈아치우면 트리와 분노가 초기화되어
            # 입력창이 곧 탈출구가 된다. 사용자가 분노를 낮출 수 있으면 제품이 무너진다.
            self._attempt()
            return

        if not task:
            # 아직 등록된 작업이 없다. 빈 줄로는 아무것도 시작하지 않는다.
            return

        self._attempt(self._start_task(task))

    def on_tree_node_selected(self, event: Tree.NodeSelected[None]) -> None:
        """트리 Enter. 입력창 Enter 와 같은 attempt 경로를 탄다."""
        event.stop()
        self._attempt(event.node)

    def _start_task(self, task: str) -> TreeNode[None]:
        """입력한 작업을 트리 루트로 세우고 상태를 초기화한다.

        새 루트를 돌려주는 이유는 reset() 직후의 cursor_node 가 아직 옛 루트를 가리키기 때문이다.
        그대로 두면 선행 작업이 트리에서 떨어져 나간 노드에 붙는다.
        """
        tree = self.query_one("#task-tree", Tree)
        tree.reset(task)
        self.state = YakState(root_task=task, seed=self._seed)
        return tree.root

    def _attempt(self, target: TreeNode[None] | None = None) -> None:
        """이걸 하려고 한다. 선행 작업 3개가 붙고 세 패널이 함께 갱신된다."""
        if self.state is None:
            return

        tree = self.query_one("#task-tree", Tree)
        attempted = target or tree.cursor_node or tree.root

        state = self.state.attempt()
        self.state = state
        self._grow_prerequisites(tree, attempted, state)

        # 남은 시간의 기준점을 지금으로 되돌린다. 그래야 줄어들던 숫자가 새 총량으로 튀어오른다.
        self._reset_elapsed_origin()

        # 구동 소스를 분리한다. 미정 표기는 분노가, 사과와 성공 확률은 회차가 구동한다.
        self._refresh_anger(state)
        self._refresh_estimate()
        self._refresh_leave_time(state)
        self._refresh_hope(state.attempt_count)
        self._announce_apology(state.attempt_count)
        self._save_session(state)

    # --- 트리 ----------------------------------------------------------------

    def _grow_prerequisites(self, tree: Tree, attempted: TreeNode[None], state: YakState) -> None:
        """시도한 작업 아래에 이번 회차의 선행 작업을 붙인다."""
        lines = prerequisites_for(state.seed, state.attempt_count, state.root_task)
        self._attach_prerequisites(tree, attempted, lines)

    def _attach_prerequisites(
        self, tree: Tree, attempted: TreeNode[None], lines: tuple[str, ...]
    ) -> TreeNode[None]:
        """선행 작업을 붙이고 커서를 첫 선행 작업으로 옮긴 뒤 그 노드를 돌려준다.

        select_node() 를 쓰지 마라. NodeSelected 를 다시 발행해 attempt 가 연쇄 호출된다.
        """
        for line in lines:
            attempted.add_leaf(line)
        attempted.expand()

        # 노드를 추가하면 줄 캐시가 무효화되어 새 노드의 줄 번호가 아직 -1 이다.
        # last_line 을 읽어 캐시를 다시 세워야 move_cursor 가 새 노드를 찾아간다.
        _ = tree.last_line

        newest = attempted.children[-PREREQ_COUNT]
        tree.move_cursor(newest)
        tree.scroll_to_node(newest, animate=False)
        return newest

    # --- 상태 패널 ------------------------------------------------------------

    def _refresh_anger(self, state: YakState) -> None:
        """분노 게이지. 최초 견적 대비 배신 배율에 비례한다."""
        progress = anger(state.seed, state.attempt_count)
        self.query_one("#anger", ProgressBar).update(progress=progress)

    def _refresh_estimate(self) -> None:
        """남은 시간. 총량은 attempt 가 정하고 줄어드는 속도는 시계가 정한다.

        예상 퇴근 시각과 헷갈리지 마라. 저쪽은 절대 시각이라 경과에 움직이지 않는다.
        """
        state = self.state
        seed = self._seed if state is None else state.seed
        attempt_count = INITIAL_ATTEMPT_COUNT if state is None else state.attempt_count

        seconds = remaining_seconds(seed, attempt_count, self._elapsed_seconds())
        self.query_one("#estimate", Static).update(f"예상 소요 {remaining_label(seconds)}")

    def _refresh_leave_time(self, state: YakState) -> None:
        """예상 퇴근 시각. 분노가 상한이면 leave_label 이 숫자를 포기한다."""
        label = leave_label(state.seed, state.attempt_count)
        self.query_one("#leave-time", Static).update(f"예상 퇴근 {label}")

    def _refresh_hope(self, attempt_count: int) -> None:
        """거짓 희망. 다음 재시도의 성공 확률은 회차가 구동한다."""
        self.query_one("#hope", Static).update(hope_line(attempt_count))

    def _announce_apology(self, attempt_count: int) -> None:
        """사과. 회차가 구동하고 6회차부터는 사라진다. 새 알림 전에 기존 알림을 지운다."""
        self.clear_notifications()
        message = apology_for(attempt_count)
        if message is not None:
            self.notify(message, timeout=APOLOGY_TIMEOUT_SEC)

    # --- 남은 시간 -------------------------------------------------------------

    def _reset_elapsed_origin(self) -> None:
        """남은 시간을 재는 기준점을 지금으로 옮긴다."""
        self._elapsed_origin = self._clock()

    def _elapsed_seconds(self) -> float:
        """기준점 이후 흐른 초. 주입 clock 이 monotonic 이라 단위는 초다."""
        return self._clock() - self._elapsed_origin

    def _tick(self) -> None:
        """1초마다 남은 시간만 다시 그린다.

        여기에 분노·사과·성공 확률을 붙이지 마라. 그 셋은 attempt 가 구동한다.
        구동 소스를 섞으면 시간이 흐르기만 해도 회차가 오른 것처럼 보인다.
        """
        self._refresh_estimate()

    # --- 상태 저장과 복원 ------------------------------------------------------

    def _restore_session(self) -> None:
        """저장된 상태가 있으면 트리와 세 패널을 그대로 되살린다.

        3연타로 겨우 탈출했는데 다시 켜면 그 지옥이 그대로 있다.
        저장된 값은 네 필드뿐이므로 나머지는 전부 여기서 재계산한다.
        """
        state = load_state(self._state_path)
        if state is None:
            return

        self.state = state
        self._rebuild_tree(state)
        self._refresh_anger(state)
        self._refresh_estimate()
        self._refresh_leave_time(state)
        self._refresh_hope(state.attempt_count)

    def _rebuild_tree(self, state: YakState) -> None:
        """회차마다 붙었던 선행 작업을 1회차부터 다시 쌓는다.

        커서는 언제나 직전 회차의 첫 선행 작업에 있었다. 그 자리를 그대로 복원해야
        복원 후의 Enter 가 끊긴 자리가 아니라 이어지는 자리에 선행 작업을 붙인다.
        """
        tree = self.query_one("#task-tree", Tree)
        tree.reset(state.root_task)

        attempted = tree.root
        for attempt_count in range(1, state.attempt_count + 1):
            lines = prerequisites_for(state.seed, attempt_count, state.root_task)
            attempted = self._attach_prerequisites(tree, attempted, lines)

    def _save_session(self, state: YakState) -> None:
        """이번 attempt 를 파일에 남긴다.

        저장은 부가 기능이다. 실패해도 로그만 남기고 attempt 자체는 그대로 굴러간다.
        """
        try:
            save_state(state, self._state_path)
        except OSError as error:
            self.log.warning(f"상태를 저장하지 못했다: {self._state_path} ({error!r})")

    # --- 종료 시퀀스 ----------------------------------------------------------

    def action_yak_quit(self, key_label: str) -> None:
        """Ctrl+C 와 Ctrl+Q. 종료 대신 배너가 뜨고 시간창 안에 세 번을 채워야 빠져나간다.

        두 키는 같은 시간창을 공유하므로 혼합 3연타도 인정된다.
        """
        now = self._clock()
        pressed = next_quit_press(self._quit_presses, self._quit_last_at, now, self._quit_window)
        self._quit_presses = pressed
        self._quit_last_at = now

        if pressed >= QUIT_SEQUENCE_LENGTH:
            # 세 번째 키는 exit 만 한다.
            # 여기서 attempt 를 부르면 마지막 갱신이 repaint 전에 사라져 화면에 안 보인다.
            self._stop_quit_timer()
            self.exit()
            return

        if pressed == 1:
            self._open_quit_banner(key_label)
        else:
            self._advance_quit_banner(key_label, pressed)

        self._restart_quit_timer()

    def _open_quit_banner(self, key_label: str) -> None:
        """시퀀스의 첫 키. attempt 를 1회 부르고 그 변화를 배너에 복제한다."""
        # 시간창이 만료됐지만 timer 가 아직 안 돈 배너를 먼저 걷어낸다.
        # 남겨두면 새 배너가 그 위에 쌓여 이전 시퀀스의 숫자가 화면에 남는다.
        self._close_quit_banner()

        state_before = self.state
        anger_before = (
            INITIAL_ANGER
            if state_before is None
            else anger(state_before.seed, state_before.attempt_count)
        )
        self._attempt()
        state = self.state

        if state is None:
            prerequisites: tuple[str, ...] = ()
            anger_after = INITIAL_ANGER
            minutes_added = NO_ADDED_MINUTES
        else:
            prerequisites = prerequisites_for(state.seed, state.attempt_count, state.root_task)
            anger_after = anger(state.seed, state.attempt_count)
            minutes_added = increment(state.seed, state.attempt_count)

        self._quit_banner = QuitBanner(
            key_label=key_label,
            pressed=self._quit_presses,
            prerequisites=prerequisites,
            anger_before=anger_before,
            anger_after=anger_after,
            minutes_added=minutes_added,
        )
        self.push_screen(self._quit_banner)

    def _advance_quit_banner(self, key_label: str, pressed: int) -> None:
        """두 번째 키. 카운터만 갱신한다. App 이 값을 먼저 정해 배너에 넘긴다."""
        if self._quit_banner is not None:
            self._quit_banner.update_counter(key_label, pressed)

    def _restart_quit_timer(self) -> None:
        """다음 키를 기다리는 시간창. 만료되면 카운터와 배너를 리셋한다."""
        self._stop_quit_timer()
        self._quit_timer = self.set_timer(self._quit_window, self._reset_quit_sequence)

    def _stop_quit_timer(self) -> None:
        if self._quit_timer is not None:
            self._quit_timer.stop()
            self._quit_timer = None

    def _reset_quit_sequence(self) -> None:
        """시간창 만료. 다음 Ctrl+C 는 새 시퀀스라 선행 작업 3개가 다시 붙는다."""
        self._quit_presses = NO_QUIT_SEQUENCE
        self._quit_last_at = None
        self._close_quit_banner()

    def _close_quit_banner(self) -> None:
        if self._quit_banner is None:
            return

        banner, self._quit_banner = self._quit_banner, None
        if self.screen is banner:
            self.pop_screen()


def main() -> None:
    """콘솔 스크립트 진입점. `uv run ralphthon-sample`이 이 함수를 호출한다."""
    RalphthonApp().run()


if __name__ == "__main__":
    main()
