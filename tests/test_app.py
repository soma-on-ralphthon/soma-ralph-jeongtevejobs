"""headless TUI 테스트.

Textual 의 run_test() 로 실제 키 입력 경로를 태운다.
파생값 계산은 test_state.py 의 순수 함수 테스트가 담당한다.
"""

from textual.widgets import Input, ProgressBar, Static, Tree

from ralphthon_sample.app import RalphthonApp
from ralphthon_sample.config import (
    APOLOGY_TIMEOUT_SEC,
    INITIAL_ESTIMATE_MIN,
    PREREQ_COUNT,
    TREE_GUIDE_DEPTH,
)
from ralphthon_sample.state import anger, leave_label, total_minutes
from ralphthon_sample.texts import apology_for, hope_rate, prerequisites_for

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
