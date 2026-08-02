"""ralphthon-sample 진입점.

Textual App, 화면 구성, 키 바인딩만 담당한다.
계산은 전부 state.py 와 texts.py 의 순수 함수에 있다. 여기에 수치 로직을 넣지 마라.
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, ProgressBar, Static, Tree
from textual.widgets.tree import TreeNode

from ralphthon_sample.config import (
    ANGER_MAX,
    APOLOGY_TIMEOUT_SEC,
    DEMO_SEED,
    INITIAL_ESTIMATE_MIN,
    PREREQ_COUNT,
    TREE_GUIDE_DEPTH,
)
from ralphthon_sample.state import YakState, anger, leave_label, leave_time_label, total_minutes
from ralphthon_sample.texts import BLOCKED_LABEL, apology_for, hope_line, prerequisites_for

PLACEHOLDER_TEXT = "오늘 처리할 작업을 한 줄로 입력하고 Enter"
EMPTY_TREE_LABEL = "아직 등록된 작업이 없습니다"
INITIAL_ANGER = 0
INITIAL_ATTEMPT_COUNT = 0


class RalphthonApp(App[None]):
    """야크 셰이빙 TUI.

    좌측 트리 2fr, 우측 상태 패널 1fr, 하단 입력창을 한 화면에 둔다.
    """

    TITLE = "ralphthon-sample"

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

    def __init__(self, seed: str = DEMO_SEED) -> None:
        super().__init__()
        self._seed = seed
        self.state: YakState | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="panels"):
            yield Tree(EMPTY_TREE_LABEL, id="task-tree")
            with Vertical(id="status"):
                yield Static("분노 게이지", id="anger-label")
                yield ProgressBar(total=ANGER_MAX, show_eta=False, id="anger")
                yield Static(f"예상 소요 {INITIAL_ESTIMATE_MIN}분", id="estimate")
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

    # --- 입력 경로 ------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """입력창 Enter. 새 작업이면 등록하고, 등록 후의 빈 Enter 는 활성 작업 재시도다."""
        task = event.value.strip()
        event.input.value = ""

        if not task:
            # 아직 등록된 작업이 없으면 _attempt 가 조용히 빠져나간다.
            self._attempt()
            return

        fresh_root = None
        if self.state is None or task != self.state.root_task:
            fresh_root = self._start_task(task)
        self._attempt(fresh_root)

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

        # 구동 소스를 분리한다. 미정 표기는 분노가, 사과와 성공 확률은 회차가 구동한다.
        self._refresh_anger(state)
        self._refresh_estimate(state)
        self._refresh_leave_time(state)
        self._refresh_hope(state.attempt_count)
        self._announce_apology(state.attempt_count)

    # --- 트리 ----------------------------------------------------------------

    def _grow_prerequisites(self, tree: Tree, attempted: TreeNode[None], state: YakState) -> None:
        """시도한 작업 아래에 선행 작업을 붙이고 커서를 첫 선행 작업으로 옮긴다.

        select_node() 를 쓰지 마라. NodeSelected 를 다시 발행해 attempt 가 연쇄 호출된다.
        """
        for line in prerequisites_for(state.seed, state.attempt_count, state.root_task):
            attempted.add_leaf(line)
        attempted.expand()

        # 노드를 추가하면 줄 캐시가 무효화되어 새 노드의 줄 번호가 아직 -1 이다.
        # last_line 을 읽어 캐시를 다시 세워야 move_cursor 가 새 노드를 찾아간다.
        _ = tree.last_line

        newest = attempted.children[-PREREQ_COUNT]
        tree.move_cursor(newest)
        tree.scroll_to_node(newest, animate=False)

    # --- 상태 패널 ------------------------------------------------------------

    def _refresh_anger(self, state: YakState) -> None:
        """분노 게이지. 최초 견적 대비 배신 배율에 비례한다."""
        progress = anger(state.seed, state.attempt_count)
        self.query_one("#anger", ProgressBar).update(progress=progress)

    def _refresh_estimate(self, state: YakState) -> None:
        """누적 견적."""
        minutes = total_minutes(state.seed, state.attempt_count)
        self.query_one("#estimate", Static).update(f"예상 소요 {minutes}분")

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


def main() -> None:
    """콘솔 스크립트 진입점. `uv run ralphthon-sample`이 이 함수를 호출한다."""
    RalphthonApp().run()


if __name__ == "__main__":
    main()
