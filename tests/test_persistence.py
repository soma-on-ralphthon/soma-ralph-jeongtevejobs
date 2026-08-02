"""상태 저장과 복원 단위 테스트.

여기서는 파일 입출력만 본다. 복원한 상태로 화면을 다시 그리는 것은 test_app.py 가 맡는다.
저장하는 값은 상태 네 필드뿐이고 트리와 파생값은 전부 재계산으로 복원된다.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import pytest

from ralphthon_sample.config import STATE_FILENAME
from ralphthon_sample.persistence import default_state_path, load_state, save_state
from ralphthon_sample.state import YakState

TASK = "버튼 색상 변경"
SEED = "test-seed"
STARTED_AT = datetime(2026, 8, 2, 22, 25)

STATE_FIELDS = {"root_task", "attempt_count", "seed", "started_at"}


def sample_state(attempt_count: int = 4) -> YakState:
    """저장 대상 상태. 네 필드를 전부 기본값이 아닌 값으로 채운다."""
    return YakState(
        root_task=TASK,
        attempt_count=attempt_count,
        seed=SEED,
        started_at=STARTED_AT,
    )


# --- 경로 ---------------------------------------------------------------------


def test_default_state_path_sits_in_the_working_directory(tmp_path: Path):
    # Arrange / Act
    path = default_state_path()

    # Assert
    # 프로젝트 루트에서 uv run ralphthon-sample 을 돌린다는 전제다.
    assert path == tmp_path / STATE_FILENAME


def test_state_filename_is_hidden_and_json():
    # Arrange / Act / Assert
    assert STATE_FILENAME.startswith(".")
    assert STATE_FILENAME.endswith(".json")


# --- 저장 ---------------------------------------------------------------------


def test_save_then_load_round_trips_every_field(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    state = sample_state()

    # Act
    save_state(state, path)
    restored = load_state(path)

    # Assert
    assert restored == state


def test_save_stores_only_the_four_state_fields(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME

    # Act
    save_state(sample_state(), path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    # Assert
    # 파생값을 저장하면 수치 모델이 바뀔 때 화면과 파일이 어긋난다.
    assert set(payload) == STATE_FIELDS


def test_save_keeps_korean_text_readable(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME

    # Act
    save_state(sample_state(), path)

    # Assert
    assert TASK in path.read_text(encoding="utf-8")


def test_save_overwrites_the_previous_snapshot(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    save_state(sample_state(attempt_count=4), path)

    # Act
    save_state(sample_state(attempt_count=7), path)
    restored = load_state(path)

    # Assert
    assert restored.attempt_count == 7


def test_save_creates_the_file_when_it_does_not_exist(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    assert not path.exists()

    # Act
    save_state(sample_state(), path)

    # Assert
    assert path.exists()


# --- 복원 실패 ----------------------------------------------------------------


def test_load_returns_none_when_the_file_is_missing(tmp_path: Path):
    # Arrange / Act / Assert
    assert load_state(tmp_path / STATE_FILENAME) is None


def test_load_returns_none_when_the_json_is_broken(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    path.write_text("{이건 JSON 이 아니다", encoding="utf-8")

    # Act / Assert
    assert load_state(path) is None


def test_load_logs_the_reason_when_the_json_is_broken(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    # Arrange
    path = tmp_path / STATE_FILENAME
    path.write_text("{이건 JSON 이 아니다", encoding="utf-8")

    # Act
    with caplog.at_level(logging.WARNING):
        load_state(path)

    # Assert
    # 조용히 새 상태로 시작하되 예외를 삼키지는 않는다.
    assert caplog.records


def test_load_returns_none_when_the_payload_is_not_an_object(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    path.write_text('["버튼 색상 변경", 4]', encoding="utf-8")

    # Act / Assert
    assert load_state(path) is None


@pytest.mark.parametrize("missing", sorted(STATE_FIELDS))
def test_load_returns_none_when_a_field_is_missing(tmp_path: Path, missing: str):
    # Arrange
    path = tmp_path / STATE_FILENAME
    save_state(sample_state(), path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload[missing]
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # Act / Assert
    assert load_state(path) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("root_task", ""),
        ("root_task", 42),
        ("attempt_count", -1),
        ("attempt_count", "네 번"),
        ("attempt_count", 1.5),
        ("seed", None),
        ("started_at", "어제 밤"),
    ],
)
def test_load_returns_none_when_a_field_is_invalid(tmp_path: Path, field: str, value: object):
    # Arrange
    path = tmp_path / STATE_FILENAME
    save_state(sample_state(), path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[field] = value
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # Act / Assert
    # 파일은 사용자가 손댈 수 있는 외부 입력이다. 경계에서 검증한다.
    assert load_state(path) is None


def test_load_returns_none_when_the_path_is_a_directory(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    path.mkdir()

    # Act / Assert
    assert load_state(path) is None


def test_load_accepts_a_zero_attempt_snapshot(tmp_path: Path):
    # Arrange
    path = tmp_path / STATE_FILENAME
    state = sample_state(attempt_count=0)

    # Act
    save_state(state, path)

    # Assert
    # 0 회차는 유효한 상태다. 아직 한 번도 시도하지 않은 최초 화면이다.
    assert load_state(path) == state
