"""headless TUI 테스트.

Textual 의 run_test() 로 실제 키 입력 경로를 태운다.
파생값 계산은 test_state.py 의 순수 함수 테스트가 담당한다.
"""

from textual.widgets import Input, ProgressBar, Static, Tree

from ralphthon_sample.app import RalphthonApp
from ralphthon_sample.config import INITIAL_ESTIMATE_MIN, PREREQ_COUNT

TASK = "버튼 색상 변경"


async def submit_task(pilot, task: str = TASK) -> None:
    """입력창에 작업을 적고 Enter 를 눌러 attempt 를 발생시킨다."""
    task_input = pilot.app.query_one("#task-input", Input)
    task_input.focus()
    task_input.value = task
    await pilot.press("enter")
    await pilot.pause()


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
