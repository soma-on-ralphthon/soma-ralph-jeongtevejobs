"""종료 배너 ModalScreen.

배경 화면의 repaint 에 기대지 않는다. 종료 키가 만들어낸 상태 변화를 배너가 스스로 복제해 보여준다.
숫자 계산은 전부 App 이 순수 함수로 끝낸 뒤 넘겨준다. 여기서는 문구로 바꾸기만 한다.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from ralphthon_sample.config import (
    PREREQ_COUNT,
    QUIT_BANNER_HEIGHT,
    QUIT_SEQUENCE_LENGTH,
)

EMPTY_PREREQUISITE_LINE = ""


class QuitBanner(ModalScreen[None]):
    """종료 3연타 안내 배너.

    모달이 떠 있는 동안 binding chain 이 이 화면에서 끊기므로 종료 키를 여기에도 둔다.
    두 바인딩 모두 App 의 같은 action 으로 보내 시간창을 공유한다.
    """

    # 기본 ModalScreen 은 뒤 화면을 dim 처리한다. 배경이 그대로 보여야 트리 변화가 읽힌다.
    DEFAULT_CSS = f"""
    QuitBanner {{
        align: center top;
        background: $background 0%;
    }}

    QuitBanner > #quit-banner {{
        dock: top;
        width: 100%;
        height: {QUIT_BANNER_HEIGHT};
        overflow: hidden hidden;
        padding: 0 1;
        background: $panel;
        border-bottom: heavy $error;
    }}

    QuitBanner Static {{
        width: 100%;
        height: 1;
        text-wrap: nowrap;
        text-overflow: ellipsis;
    }}

    QuitBanner #quit-counter {{
        text-style: bold;
        color: $error;
    }}
    """

    BINDINGS = [
        Binding("ctrl+c", "app.yak_quit('Ctrl+C')", "종료 시도", priority=True),
        Binding("ctrl+q", "app.yak_quit('Ctrl+Q')", "종료 시도", priority=True),
    ]

    def __init__(
        self,
        *,
        key_label: str,
        pressed: int,
        prerequisites: tuple[str, ...],
        anger_before: int,
        anger_after: int,
        minutes_added: int,
    ) -> None:
        super().__init__()
        self._key_label = key_label
        self._pressed = pressed
        self._prerequisites = prerequisites
        self._anger_before = anger_before
        self._anger_after = anger_after
        self._minutes_added = minutes_added

    @property
    def counter_line(self) -> str:
        """`Ctrl+C 1/3`. 어느 키를 눌렀는지까지 그대로 보여준다."""
        return f"{self._key_label} {self._pressed}/{QUIT_SEQUENCE_LENGTH}"

    @property
    def anger_line(self) -> str:
        """`분노 86 → 100`. 상수가 아니라 첫 종료 키 직전과 직후 값이다."""
        return f"분노 {self._anger_before} → {self._anger_after}"

    @property
    def total_line(self) -> str:
        """`누적 +89분`. 이번 attempt 가 밀어낸 견적이다."""
        return f"누적 +{self._minutes_added}분"

    def compose(self) -> ComposeResult:
        with Vertical(id="quit-banner"):
            yield Static(self.counter_line, id="quit-counter")
            for index, line in enumerate(self._banner_prerequisites()):
                yield Static(line, id=f"quit-prereq-{index}")
            yield Static(self.anger_line, id="quit-anger")
            yield Static(self.total_line, id="quit-total")

    def update_counter(self, key_label: str, pressed: int) -> None:
        """두 번째 키. 카운터만 갱신한다.

        App 이 값을 먼저 넘겨주므로 mount 전이어도 compose 가 최신 값을 그린다.
        """
        self._key_label = key_label
        self._pressed = pressed
        if self.is_mounted:
            self.query_one("#quit-counter", Static).update(self.counter_line)

    def _banner_prerequisites(self) -> tuple[str, ...]:
        """선행 작업 줄. 높이가 흔들리지 않도록 언제나 PREREQ_COUNT 행을 채운다."""
        padding = (EMPTY_PREREQUISITE_LINE,) * PREREQ_COUNT
        return (self._prerequisites + padding)[:PREREQ_COUNT]
