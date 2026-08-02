"""ralphthon-sample 진입점.

Textual App, 화면 구성, 키 바인딩만 담당한다.
계산은 전부 state.py 와 texts.py 의 순수 함수에 있다. 여기에 수치 로직을 넣지 마라.
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, ProgressBar, Static, Tree

from ralphthon_sample.config import ANGER_MAX, DEFAULT_SEED, INITIAL_ESTIMATE_MIN
from ralphthon_sample.state import YakState, leave_time_label
from ralphthon_sample.texts import prerequisites_for

PLACEHOLDER_TEXT = "오늘 처리할 작업을 한 줄로 입력하고 Enter"
EMPTY_TREE_LABEL = "아직 등록된 작업이 없습니다"
INITIAL_ANGER = 0


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

    def __init__(self, seed: str = DEFAULT_SEED) -> None:
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
        yield Input(placeholder=PLACEHOLDER_TEXT, id="task-input")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#anger", ProgressBar).update(progress=INITIAL_ANGER)
        self.query_one("#task-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """입력창 Enter. 빈 입력은 무시한다."""
        task = event.value.strip()
        if not task:
            return

        # 새 작업 이름이면 트리를 그 작업으로 다시 세운다.
        # 같은 이름이면 기존 트리에 선행 작업을 더 붙인다. 완료 개념은 없다.
        if self.state is None or task != self.state.root_task:
            self._start_task(task)
        self._attempt()
        event.input.value = ""

    def _start_task(self, task: str) -> None:
        """입력한 작업을 트리 루트로 세우고 상태를 초기화한다."""
        self.query_one("#task-tree", Tree).reset(task)
        self.state = YakState(root_task=task, seed=self._seed)

    def _attempt(self) -> None:
        """이걸 하려고 한다. 선행 작업 3개가 붙고 시도 횟수가 하나 올라간다."""
        if self.state is None:
            return

        state = self.state.attempt()
        self.state = state
        tree = self.query_one("#task-tree", Tree)
        for line in prerequisites_for(state.seed, state.attempt_count, state.root_task):
            tree.root.add_leaf(line)
        tree.root.expand()


def main() -> None:
    """콘솔 스크립트 진입점. `uv run ralphthon-sample`이 이 함수를 호출한다."""
    RalphthonApp().run()


if __name__ == "__main__":
    main()
