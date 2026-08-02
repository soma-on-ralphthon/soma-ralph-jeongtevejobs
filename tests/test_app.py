"""headless TUI 테스트.

Textual 의 run_test() 로 실제 키 입력 경로를 태운다.
파생값 계산은 test_state.py 의 순수 함수 테스트가 담당한다.
"""

from pathlib import Path

from textual.widgets import Input, ProgressBar, Static, Tree

from ralphthon_sample.app import RalphthonApp
from ralphthon_sample.config import (
    APOLOGY_TIMEOUT_SEC,
    DEMO_SEED,
    INITIAL_ESTIMATE_MIN,
    PREREQ_COUNT,
    QUIT_BANNER_HEIGHT,
    QUIT_SEQUENCE_LENGTH,
    QUIT_WINDOW_SEC,
    STATE_FILENAME,
    TREE_GUIDE_DEPTH,
)
from ralphthon_sample.state import anger, increment, leave_label, total_minutes
from ralphthon_sample.texts import apology_for, hope_rate, prerequisites_for
from ralphthon_sample.widgets.quit_banner import QuitBanner

TASK = "버튼 색상 변경"
SEED = "test-seed"


async def submit_task(pilot, task: str = TASK) -> None:
    """입력창에 작업을 적고 Enter 를 눌러 attempt 를 발생시킨다."""
    task_input = pilot.app.query_one("#task-input", Input)
    task_input.focus()
    task_input.value = task
    await pilot.press("enter")
    await pilot.pause()


async def press_enter_on_tree(pilot) -> None:
    """트리에 포커스를 주고 Enter 를 눌러 커서 노드에서 attempt 를 발생시킨다."""
    pilot.app.query_one("#task-tree", Tree).focus()
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


def panel_text(pilot, selector: str) -> str:
    """상태 패널 Static 의 본문. Textual 8 에서는 renderable 이 아니라 content 다."""
    return str(pilot.app.query_one(selector, Static).content)


def screen_text(pilot, selector: str) -> str:
    """활성 화면 Static 의 본문.

    App.query_one 은 화면 스택 top 이 아니라 기본 화면을 뒤진다. 모달은 화면에서 직접 찾아야 한다.
    """
    return str(pilot.app.screen.query_one(selector, Static).content)


def count_nodes(node) -> int:
    """루트를 뺀 전체 자손 수. 무한 후퇴가 깊어져도 세어야 한다."""
    return sum(1 + count_nodes(child) for child in node.children)


async def test_three_panels_are_mounted_together():
    # Arrange
    app = RalphthonApp(seed="test-seed")

    # Act
    async with app.run_test() as pilot:
        # Assert
        assert pilot.app.query_one("#task-tree", Tree) is not None
        assert pilot.app.query_one("#anger", ProgressBar) is not None
        assert pilot.app.query_one("#leave-time", Static) is not None
        assert pilot.app.query_one("#task-input", Input) is not None


async def test_initial_screen_shows_five_minutes_and_twenty_two_thirty():
    # Arrange
    app = RalphthonApp(seed="test-seed")

    # Act
    async with app.run_test() as pilot:
        estimate = pilot.app.query_one("#estimate", Static).content
        leave_time = pilot.app.query_one("#leave-time", Static).content

        # Assert
        assert f"{INITIAL_ESTIMATE_MIN}분" in str(estimate)
        assert "22:30" in str(leave_time)


async def test_initial_anger_is_zero():
    # Arrange
    app = RalphthonApp(seed="test-seed")

    # Act
    async with app.run_test() as pilot:
        # Assert
        assert pilot.app.query_one("#anger", ProgressBar).progress == 0


async def test_submitting_a_task_adds_exactly_three_prerequisites():
    # Arrange
    app = RalphthonApp(seed="test-seed")

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        root = pilot.app.query_one("#task-tree", Tree).root

        # Assert
        assert len(root.children) == PREREQ_COUNT


async def test_submitted_task_becomes_the_tree_root():
    # Arrange
    app = RalphthonApp(seed="test-seed")

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        root = pilot.app.query_one("#task-tree", Tree).root

        # Assert
        assert TASK in str(root.label)


async def test_prerequisite_labels_are_distinct_and_name_the_task():
    # Arrange
    app = RalphthonApp(seed="test-seed")

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        tree = pilot.app.query_one("#task-tree", Tree)
        labels = [str(child.label) for child in tree.root.children]

        # Assert
        assert len(set(labels)) == PREREQ_COUNT
        assert all(TASK in label for label in labels)


async def test_submitting_records_one_attempt_and_clears_the_input():
    # Arrange
    app = RalphthonApp(seed="test-seed")

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)

        # Assert
        assert pilot.app.state is not None
        assert pilot.app.state.attempt_count == 1
        assert pilot.app.query_one("#task-input", Input).value == ""


async def test_blank_input_does_not_create_a_task():
    # Arrange
    app = RalphthonApp(seed="test-seed")

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot, task="   ")

        # Assert
        assert pilot.app.state is None
        assert len(pilot.app.query_one("#task-tree", Tree).root.children) == 0


# --- 하나의 attempt 경로 ------------------------------------------------------


async def test_input_enter_and_tree_enter_take_the_same_attempt_path():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        after_input = (pilot.app.state.attempt_count, count_nodes(pilot.app.query_one(Tree).root))

        await press_enter_on_tree(pilot)
        after_tree = (pilot.app.state.attempt_count, count_nodes(pilot.app.query_one(Tree).root))

        # Assert
        # 입력창 Enter 든 트리 Enter 든 결과는 같다. attempt 가 1 올라가고 선행 작업 3개가 붙는다.
        assert after_input == (1, PREREQ_COUNT)
        assert after_tree == (2, PREREQ_COUNT * 2)


async def test_empty_enter_after_registration_is_another_attempt():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        await submit_task(pilot, task="")

        # Assert
        # 최초 등록 후의 빈 Enter 도 "이걸 하려고 한다"다. 완료 개념은 없다.
        assert pilot.app.state.attempt_count == 2


async def test_typing_another_task_after_registration_is_another_attempt():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        await submit_task(pilot, task="완전히 다른 작업")
        tree = pilot.app.query_one("#task-tree", Tree)

        # Assert
        # 최초 등록 후에는 무엇을 적고 Enter 를 눌러도 결과가 같다. 활성 작업 재시도다.
        # 루트를 갈아치우면 트리가 통째로 날아가 무한 후퇴가 끊긴다.
        assert pilot.app.state.root_task == TASK
        assert TASK in str(tree.root.label)
        assert pilot.app.state.attempt_count == 2
        assert count_nodes(tree.root) == PREREQ_COUNT * 2


async def test_typing_another_task_never_lowers_the_anger():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        for _ in range(5):
            await submit_task(pilot)
        before = pilot.app.query_one("#anger", ProgressBar).progress

        await submit_task(pilot, task="퇴근하기")
        after = pilot.app.query_one("#anger", ProgressBar).progress

        # Assert
        # 입력창으로 분노를 되돌릴 수 있으면 제품이 무너진다. 탈출구를 만들지 마라.
        assert before == anger(SEED, 5)
        assert after == anger(SEED, 6)
        assert after > before


async def test_typing_another_task_cannot_wipe_a_restored_session(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    async with RalphthonApp(seed=SEED, state_path=path).run_test() as pilot:
        await submit_task(pilot)
        await submit_task(pilot, task="")

    # Act
    async with RalphthonApp(seed=SEED, state_path=path).run_test() as pilot:
        await submit_task(pilot, task="이번엔 진짜 새 작업")
        tree = pilot.app.query_one("#task-tree", Tree)

        # Assert
        # 다시 켜도 그 지옥이 그대로 있어야 한다. 입력창이 초기화 버튼이 되면 안 된다.
        assert pilot.app.state.root_task == TASK
        assert pilot.app.state.attempt_count == 3
        assert count_nodes(tree.root) == PREREQ_COUNT * 3


async def test_cursor_moves_to_the_first_new_prerequisite():
    # Arrange
    app = RalphthonApp(seed=SEED)
    expected = prerequisites_for(SEED, 1, TASK)[0]

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        cursor = pilot.app.query_one("#task-tree", Tree).cursor_node

        # Assert
        assert str(cursor.label) == expected


async def test_new_prerequisites_hang_under_the_attempted_node():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        attempted = pilot.app.query_one("#task-tree", Tree).cursor_node
        await press_enter_on_tree(pilot)

        # Assert
        # 선행 작업을 처리하려 하면 그 선행 작업이 또 생긴다. 무한 후퇴다.
        assert len(attempted.children) == PREREQ_COUNT


async def test_tree_guide_depth_is_two():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        # Assert
        assert pilot.app.query_one("#task-tree", Tree).guide_depth == TREE_GUIDE_DEPTH


# --- 키보드 전용 조작 ---------------------------------------------------------
#
# PRODUCT.md Success criteria "모든 핵심 행동을 실제 터미널에서
# 키보드만으로 수행할 수 있다" 의 회귀 잠금.
# 다른 headless 테스트는 focus() 와 value 대입으로 지름길을 탄다.
# 그래서 포커스가 트리에 닿지 않거나 Input 이 문자를 잃어도 전부 통과한다.
# 여기서는 지름길을 쓰지 않고 키 입력만으로 같은 경로를 태운다.


async def type_text(pilot, text: str) -> None:
    """한 글자씩 실제 키로 친다. focus() 도 value 대입도 쓰지 않는다."""
    for character in text:
        await pilot.press(character)
    await pilot.pause()


async def test_input_holds_the_focus_on_startup():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        # Assert
        # 첫 키가 입력창에 들어가야 마우스 없이 작업을 등록할 수 있다.
        assert pilot.app.focused.id == "task-input"


async def test_focus_chain_holds_only_the_two_interactive_widgets():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        # Assert
        # Tab 정거장이 이 둘뿐이어야 트리까지 한 번에 닿는다.
        # 포커스를 받는 위젯이 끼어들면 사용자가 Tab 을 몇 번 눌러야 하는지 알 수 없게 된다.
        assert [widget.id for widget in pilot.app.screen.focus_chain] == ["task-tree", "task-input"]


async def test_task_is_registered_with_keystrokes_only():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await type_text(pilot, TASK)
        await pilot.press("enter")
        await pilot.pause()
        tree = pilot.app.query_one("#task-tree", Tree)

        # Assert
        assert str(tree.root.label) == TASK
        assert pilot.app.state.attempt_count == 1
        assert len(tree.root.children) == PREREQ_COUNT


async def test_tab_moves_the_focus_to_the_tree_and_back():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await pilot.press("tab")
        await pilot.pause()
        on_tree = pilot.app.focused.id

        await pilot.press("shift+tab")
        await pilot.pause()

        # Assert
        # 입력창과 트리를 오갈 수 없으면 트리 Enter 경로가 키보드로는 죽은 경로가 된다.
        assert on_tree == "task-tree"
        assert pilot.app.focused.id == "task-input"


async def test_tree_attempt_is_reachable_with_the_keyboard_alone():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await type_text(pilot, TASK)
        await pilot.press("enter")
        await pilot.pause()

        # 입력창 -> 트리로 옮겨 커서를 내리고 그 선행 작업을 시도한다.
        await pilot.press("tab", "down")
        await pilot.pause()
        tree = pilot.app.query_one("#task-tree", Tree)
        attempted = tree.cursor_node

        await pilot.press("enter")
        await pilot.pause()

        # Assert
        # 트리에서 노드를 고르고 Enter 를 누르는 것도 입력창 Enter 와 같은 attempt 다.
        assert attempted is not tree.root
        assert pilot.app.state.attempt_count == 2
        assert count_nodes(tree.root) == PREREQ_COUNT * 2
        assert len(attempted.children) == PREREQ_COUNT
        # 커서는 방금 생긴 첫 선행 작업으로 따라간다.
        assert tree.cursor_node is attempted.children[0]


async def test_letter_keys_are_typed_into_the_input():
    # Arrange
    app = RalphthonApp(seed=SEED)
    typed = "quit"

    # Act
    async with app.run_test() as pilot:
        await type_text(pilot, typed)

        # Assert
        # AGENTS.md 의 "q 키를 전역 바인딩으로 만들지 마라" 가 지키려는 결과를 잠근다.
        # 글자 키는 종료도 다른 action 도 아니고 그대로 입력창에 들어가야 한다.
        assert pilot.app.query_one("#task-input", Input).value == typed
        assert pilot.app.focused.id == "task-input"
        assert pilot.app.is_running


# --- 파생값 패널 -------------------------------------------------------------


async def test_three_panels_update_together_in_one_attempt():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)

        # Assert
        # 트리, 분노, 퇴근 시간이 하나의 attempt 마다 원자적으로 함께 갱신된다.
        assert len(pilot.app.query_one("#task-tree", Tree).root.children) == PREREQ_COUNT
        assert pilot.app.query_one("#anger", ProgressBar).progress == anger(SEED, 1)
        assert f"{total_minutes(SEED, 1)}분" in panel_text(pilot, "#estimate")
        assert leave_label(SEED, 1) in panel_text(pilot, "#leave-time")


async def test_initial_screen_shows_ninety_seven_percent():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        # Assert
        # hope_rate(0) 이 아직 한 번도 시도하지 않은 최초 화면의 값이다.
        assert f"{hope_rate(0)}%" in panel_text(pilot, "#hope")


async def test_hope_rate_drops_after_each_attempt():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)

        # Assert
        assert f"{hope_rate(1)}%" in panel_text(pilot, "#hope")


# --- 사과 ---------------------------------------------------------------------


async def test_apology_is_notified_with_a_short_timeout(monkeypatch):
    # Arrange
    app = RalphthonApp(seed=SEED)
    calls: list[tuple[str, float | None]] = []

    # Act
    async with app.run_test() as pilot:
        monkeypatch.setattr(
            pilot.app,
            "notify",
            lambda message, **kwargs: calls.append((message, kwargs.get("timeout"))),
        )
        await submit_task(pilot)

        # Assert
        # Toast DOM 을 단언하지 않는다. run_test() 의 notifications 기본값이 False 다.
        assert calls == [(apology_for(1), APOLOGY_TIMEOUT_SEC)]


async def test_apology_disappears_from_the_sixth_attempt(monkeypatch):
    # Arrange
    app = RalphthonApp(seed=SEED)
    calls: list[str] = []

    # Act
    async with app.run_test() as pilot:
        monkeypatch.setattr(pilot.app, "notify", lambda message, **kwargs: calls.append(message))
        await submit_task(pilot)
        for _ in range(5):
            await submit_task(pilot, task="")

        # Assert
        assert pilot.app.state.attempt_count == 6
        assert calls == list(apology_for(n) for n in range(1, 6))


# --- 종료 배너와 3연타 탈출 ---------------------------------------------------


class FakeClock:
    """App 에 주입하는 clock.

    time.monotonic 을 전역 monkeypatch 하면 Textual timer 와 Toast 가 오염된다.
    """

    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


async def test_active_bindings_register_both_quit_keys():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        bindings = pilot.app.screen.active_bindings

        # Assert
        assert "ctrl+c" in bindings
        assert "ctrl+q" in bindings


def test_command_palette_is_disabled():
    # Arrange / Act / Assert
    # Ctrl+P 팔레트의 Quit 이 살아 있으면 3연타를 우회할 수 있다.
    assert RalphthonApp.ENABLE_COMMAND_PALETTE is False


async def test_one_quit_key_shows_the_banner_instead_of_quitting():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        await pilot.press("ctrl+c")
        await pilot.pause()

        # Assert
        assert pilot.app.is_running
        assert isinstance(pilot.app.screen, QuitBanner)
        assert screen_text(pilot, "#quit-counter") == f"Ctrl+C 1/{QUIT_SEQUENCE_LENGTH}"


async def test_first_quit_key_adds_three_prerequisites():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        # 배너가 뜨면 App.query_one 이 모달 화면을 뒤지므로 트리를 미리 잡아둔다.
        tree = pilot.app.query_one("#task-tree", Tree)
        before = count_nodes(tree.root)
        await pilot.press("ctrl+c")
        await pilot.pause()

        # Assert
        # 종료 시도가 곧 8회차 attempt 다.
        assert pilot.app.state.attempt_count == 2
        assert count_nodes(tree.root) == before + PREREQ_COUNT


async def test_banner_repeats_the_new_prerequisites():
    # Arrange
    app = RalphthonApp(seed=SEED)
    expected = list(prerequisites_for(SEED, 2, TASK))

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        await pilot.press("ctrl+c")
        await pilot.pause()
        lines = [screen_text(pilot, f"#quit-prereq-{index}") for index in range(PREREQ_COUNT)]

        # Assert
        # 배너는 배경 repaint 에 기대지 않고 상태 변화를 스스로 복제해 보여준다.
        assert lines == expected


async def test_banner_shows_the_anger_and_estimate_transition():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        before = anger(SEED, 1)
        await pilot.press("ctrl+c")
        await pilot.pause()

        # Assert
        # 분노는 상수가 아니라 첫 종료 키 직전과 직후 값으로 계산한다.
        assert screen_text(pilot, "#quit-anger") == f"분노 {before} → {anger(SEED, 2)}"
        assert screen_text(pilot, "#quit-total") == f"누적 +{increment(SEED, 2)}분"


async def test_banner_is_seven_rows_tall():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        await pilot.press("ctrl+c")
        await pilot.pause()

        # Assert
        # 콘텐츠 6행(카운터 1 + 선행 작업 3 + 분노 1 + 누적 1)에 하단 border 1행이다.
        assert pilot.app.screen.query_one("#quit-banner").outer_size.height == QUIT_BANNER_HEIGHT


async def test_second_quit_key_only_advances_the_counter():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        tree = pilot.app.query_one("#task-tree", Tree)
        await pilot.press("ctrl+c")
        after_first = (pilot.app.state.attempt_count, count_nodes(tree.root))

        await pilot.press("ctrl+q")
        await pilot.pause()

        # Assert
        # 두 번째 키는 카운터만 갱신한다. attempt 는 시퀀스의 첫 키에서만 1회다.
        assert (pilot.app.state.attempt_count, count_nodes(tree.root)) == after_first
        assert screen_text(pilot, "#quit-counter") == f"Ctrl+Q 2/{QUIT_SEQUENCE_LENGTH}"


async def test_three_quit_keys_inside_the_window_exit():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        await pilot.press("ctrl+c", "ctrl+c", "ctrl+c")
        await pilot.pause()

        # Assert
        assert not pilot.app.is_running


async def test_mixed_quit_keys_inside_the_window_exit():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        await pilot.press("ctrl+c", "ctrl+q", "ctrl+c")
        await pilot.pause()

        # Assert
        # Ctrl+C 와 Ctrl+Q 는 같은 시간창을 공유한다.
        assert not pilot.app.is_running


async def test_third_quit_key_does_not_run_another_attempt():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        tree = pilot.app.query_one("#task-tree", Tree)
        await pilot.press("ctrl+c", "ctrl+q")
        after_first = (pilot.app.state.attempt_count, count_nodes(tree.root))

        await pilot.press("ctrl+c")
        await pilot.pause()

        # Assert
        # 세 번째 키에서 attempt 를 부르면 마지막 갱신이 repaint 전에 사라진다.
        assert (pilot.app.state.attempt_count, count_nodes(tree.root)) == after_first


async def test_expired_window_resets_the_counter_and_grows_the_tree_again():
    # Arrange
    clock = FakeClock()
    app = RalphthonApp(seed=SEED, clock=clock)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        tree = pilot.app.query_one("#task-tree", Tree)
        await pilot.press("ctrl+c")
        clock.advance(QUIT_WINDOW_SEC + 0.1)
        await pilot.press("ctrl+c")
        await pilot.pause()

        # Assert
        # 리셋 후의 Ctrl+C 는 새 시퀀스다. 종료를 여러 번 시도할수록 트리가 계속 늘어난다.
        assert pilot.app.is_running
        assert screen_text(pilot, "#quit-counter") == f"Ctrl+C 1/{QUIT_SEQUENCE_LENGTH}"
        assert pilot.app.state.attempt_count == 3
        assert count_nodes(tree.root) == PREREQ_COUNT * 3


async def test_expired_window_closes_the_banner():
    # Arrange
    # 시간창을 짧게 주입해 timer 경로를 실제로 태운다.
    app = RalphthonApp(seed=SEED, quit_window=0.4)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)
        await pilot.press("ctrl+c")
        assert isinstance(pilot.app.screen, QuitBanner)

        await pilot.pause(0.8)

        # Assert
        assert not isinstance(pilot.app.screen, QuitBanner)


async def test_quit_sequence_survives_an_empty_session():
    # Arrange
    app = RalphthonApp(seed=SEED)

    # Act
    async with app.run_test() as pilot:
        await pilot.press("ctrl+c")
        await pilot.pause()

        # Assert
        # 작업을 등록하기 전에도 한 번의 Ctrl+C 로는 빠져나갈 수 없다.
        assert pilot.app.is_running
        assert isinstance(pilot.app.screen, QuitBanner)


# --- DEMO_SEED 데모 클라이맥스 -------------------------------------------------
#
# PRODUCT.md Happy path 5~7 의 회귀 잠금.
# 수치 자체는 test_state.py 의 DEMO_SEED_INCREMENTS 가 잠근다.
# 여기서는 그 수열이 실제 화면과 배너까지 배선되는지를 본다.
# 다른 headless 테스트는 전부 seed="test-seed" 로 도니까,
# 기본 seed 가 바뀌거나 패널 배선이 끊겨도 순수 테스트만으로는 데모가 죽은 걸 알 수 없다.

# DEMO_SEED 증가폭 (3, 5, 7, 11, 21, 18, 43, 98) 에서 따라 나오는 값이다.
CLIMAX_ATTEMPT = 7
CLIMAX_TOTAL_MIN = 113  # 5 + 108
CLIMAX_ANGER = 76  # (7 * 108 + 5) // 10
CLIMAX_LEAVE_LABEL = "익일 00:18"  # 22:25 + 113분
CLIMAX_HOPE_RATE = 21

QUIT_ATTEMPT = 8
QUIT_ADDED_MIN = 98
QUIT_ANGER = 100  # (7 * 206 + 5) // 10 은 144 라 상한에 걸린다
QUIT_LEAVE_LABEL = "미정"


async def attempt_until(pilot, attempt_count: int) -> None:
    """작업을 등록하고 목표 회차까지 빈 Enter 를 반복한다."""
    await submit_task(pilot)
    for _ in range(attempt_count - 1):
        await submit_task(pilot, task="")


async def test_demo_seed_is_the_default_of_the_app():
    # Arrange
    # seed 를 넘기지 않는다. `uv run ralphthon-sample` 이 타는 경로 그대로다.
    app = RalphthonApp()

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)

        # Assert
        # 기본 seed 가 DEMO_SEED 가 아니면 아래 클라이맥스 회귀가 통째로 무의미해진다.
        assert pilot.app.state.seed == DEMO_SEED


async def test_demo_seed_seventh_attempt_pushes_leaving_past_midnight():
    # Arrange
    app = RalphthonApp()

    # Act
    async with app.run_test() as pilot:
        await attempt_until(pilot, CLIMAX_ATTEMPT)

        # Assert
        # 7회차에 퇴근 시간이 자정을 넘는다. 분노는 아직 100 미만이라 "미정"에 가려지지 않는다.
        assert pilot.app.state.attempt_count == CLIMAX_ATTEMPT
        assert f"{CLIMAX_TOTAL_MIN}분" in panel_text(pilot, "#estimate")
        assert panel_text(pilot, "#leave-time") == f"예상 퇴근 {CLIMAX_LEAVE_LABEL}"
        assert pilot.app.query_one("#anger", ProgressBar).progress == CLIMAX_ANGER
        assert f"{CLIMAX_HOPE_RATE}%" in panel_text(pilot, "#hope")


async def test_demo_seed_first_quit_key_maxes_anger_and_gives_up_on_the_clock():
    # Arrange
    app = RalphthonApp()

    # Act
    async with app.run_test() as pilot:
        await attempt_until(pilot, CLIMAX_ATTEMPT)
        # 배너가 뜨면 App.query_one 이 모달 화면을 뒤진다. 배경 패널을 미리 잡아둔다.
        leave_time = pilot.app.query_one("#leave-time", Static)
        anger_bar = pilot.app.query_one("#anger", ProgressBar)

        await pilot.press("ctrl+c")
        await pilot.pause()

        # Assert
        # 종료 시도가 곧 8회차다. Enter 로 미리 100까지 가버리면 이 전환이 죽는다.
        assert pilot.app.is_running
        assert pilot.app.state.attempt_count == QUIT_ATTEMPT
        assert anger_bar.progress == QUIT_ANGER
        assert str(leave_time.content) == f"예상 퇴근 {QUIT_LEAVE_LABEL}"


async def test_demo_seed_quit_banner_shows_the_climax_transition():
    # Arrange
    app = RalphthonApp()

    # Act
    async with app.run_test() as pilot:
        await attempt_until(pilot, CLIMAX_ATTEMPT)
        await pilot.press("ctrl+c")
        await pilot.pause()

        # Assert
        # 배너가 그 전환을 함께 보여준다. 배경 repaint 에 기대지 않는다.
        assert screen_text(pilot, "#quit-counter") == f"Ctrl+C 1/{QUIT_SEQUENCE_LENGTH}"
        assert screen_text(pilot, "#quit-anger") == f"분노 {CLIMAX_ANGER} → {QUIT_ANGER}"
        assert screen_text(pilot, "#quit-total") == f"누적 +{QUIT_ADDED_MIN}분"


# --- 상태 저장과 복원 ---------------------------------------------------------


def tree_labels(node) -> list[str]:
    """루트를 뺀 전체 자손 라벨. 트리 모양까지 비교하려고 깊이 우선으로 훑는다."""
    labels: list[str] = []
    for child in node.children:
        labels.append(str(child.label))
        labels.extend(tree_labels(child))
    return labels


def session_fingerprint(pilot) -> tuple:
    """화면에 보이는 것 전부. 껐다 켠 뒤 이 값이 같아야 복원된 것이다."""
    tree = pilot.app.query_one("#task-tree", Tree)
    return (
        str(tree.root.label),
        tree_labels(tree.root),
        pilot.app.query_one("#anger", ProgressBar).progress,
        panel_text(pilot, "#estimate"),
        panel_text(pilot, "#leave-time"),
        panel_text(pilot, "#hope"),
    )


async def test_attempt_writes_a_snapshot(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    app = RalphthonApp(seed=SEED, state_path=path)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)

        # Assert
        assert path.exists()


async def test_restart_restores_the_same_tree_and_panels(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    async with RalphthonApp(seed=SEED, state_path=path).run_test() as pilot:
        await submit_task(pilot)
        await submit_task(pilot, task="")
        await submit_task(pilot, task="")
        before = session_fingerprint(pilot)

    # Act
    # 저장된 seed 로 복원되는지 보려고 일부러 다른 seed 로 다시 띄운다.
    async with RalphthonApp(seed="다른-seed", state_path=path).run_test() as pilot:
        after = session_fingerprint(pilot)

        # Assert
        # 3연타로 겨우 탈출했는데 다시 켜면 그 지옥이 그대로 있다.
        assert pilot.app.state.attempt_count == 3
        assert pilot.app.state.seed == SEED
        assert count_nodes(pilot.app.query_one("#task-tree", Tree).root) == PREREQ_COUNT * 3
    assert after == before


async def test_restored_session_continues_the_chain(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    async with RalphthonApp(seed=SEED, state_path=path).run_test() as pilot:
        await submit_task(pilot)
        await submit_task(pilot, task="")

    # Act
    async with RalphthonApp(seed=SEED, state_path=path).run_test() as pilot:
        await press_enter_on_tree(pilot)
        tree = pilot.app.query_one("#task-tree", Tree)

        # Assert
        # 복원된 커서가 마지막 선행 작업에 있어야 무한 후퇴가 끊기지 않고 이어진다.
        assert pilot.app.state.attempt_count == 3
        assert count_nodes(tree.root) == PREREQ_COUNT * 3
        assert str(tree.cursor_node.label) == prerequisites_for(SEED, 3, TASK)[0]


async def test_quit_sequence_attempt_survives_a_restart(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    async with RalphthonApp(seed=SEED, state_path=path).run_test() as pilot:
        await submit_task(pilot)
        await pilot.press("ctrl+c")
        await pilot.pause()

    # Act
    async with RalphthonApp(seed=SEED, state_path=path).run_test() as pilot:
        # Assert
        # 종료 키가 만든 8회차도 저장된다. 다시 켜도 분노는 내려가지 않는다.
        assert pilot.app.state.attempt_count == 2
        assert count_nodes(pilot.app.query_one("#task-tree", Tree).root) == PREREQ_COUNT * 2


async def test_restart_without_a_snapshot_starts_fresh(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    app = RalphthonApp(seed=SEED, state_path=path)

    # Act
    async with app.run_test() as pilot:
        # Assert
        assert pilot.app.state is None
        assert len(pilot.app.query_one("#task-tree", Tree).root.children) == 0
        assert f"{INITIAL_ESTIMATE_MIN}분" in panel_text(pilot, "#estimate")


async def test_restart_with_a_broken_snapshot_starts_fresh(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    path.write_text("{이건 JSON 이 아니다", encoding="utf-8")
    app = RalphthonApp(seed=SEED, state_path=path)

    # Act
    async with app.run_test() as pilot:
        # Assert
        # 깨진 파일 때문에 앱이 죽으면 안 된다. 조용히 새 상태로 시작한다.
        assert pilot.app.is_running
        assert pilot.app.state is None
        assert "22:30" in panel_text(pilot, "#leave-time")


async def test_unwritable_snapshot_path_does_not_break_the_attempt(tmp_path: Path):
    # Arrange
    # 디렉터리를 저장 경로로 주면 쓰기가 반드시 실패한다.
    path = tmp_path / STATE_FILENAME
    path.mkdir()
    app = RalphthonApp(seed=SEED, state_path=path)

    # Act
    async with app.run_test() as pilot:
        await submit_task(pilot)

        # Assert
        # 저장은 부가 기능이다. 실패해도 attempt 자체는 그대로 굴러가야 한다.
        assert pilot.app.is_running
        assert pilot.app.state.attempt_count == 1
        assert count_nodes(pilot.app.query_one("#task-tree", Tree).root) == PREREQ_COUNT
