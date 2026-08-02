"""seed scaffold headless smoke test.

Textual 앱이 headless로 부팅되고 위젯이 마운트되는지만 확인한다.
제품 동작 테스트는 core task에서 추가한다.
"""

from ralphthon_sample.app import PLACEHOLDER_TEXT, RalphthonApp


async def test_app_boots_headless():
    # Arrange
    app = RalphthonApp()

    # Act
    async with app.run_test() as pilot:
        # Assert
        assert pilot.app.is_running
        assert pilot.app.query_one("#task-tree") is not None


async def test_placeholder_text_is_not_empty():
    # Arrange / Act / Assert
    assert PLACEHOLDER_TEXT.strip()
