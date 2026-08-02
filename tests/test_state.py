"""순수 함수와 상태 단위 테스트.

여기서는 Textual 을 import 하지 않는다. state.py 와 texts.py 는 렌더링과 무관해야 한다.
"""

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from ralphthon_sample.config import (
    ANGER_MAX,
    BASE_TIME,
    INITIAL_ESTIMATE_MIN,
    NOISE_CLAMP,
    NOISE_SIGMA,
    PREREQ_COUNT,
)
from ralphthon_sample.state import YakState, leave_time_label
from ralphthon_sample.texts import PREREQUISITE_TEMPLATES, prerequisites_for

FIXED_STARTED_AT = datetime(2026, 8, 2, 22, 25)


def make_state(**overrides) -> YakState:
    """테스트용 기본 상태. started_at 을 고정해 재현 가능하게 만든다."""
    fields = {
        "root_task": "버튼 색상 변경",
        "attempt_count": 0,
        "seed": "test-seed",
        "started_at": FIXED_STARTED_AT,
    }
    return YakState(**{**fields, **overrides})


# --- config -----------------------------------------------------------------


def test_config_matches_product_spec():
    # Arrange / Act / Assert
    assert (BASE_TIME.hour, BASE_TIME.minute) == (22, 25)
    assert INITIAL_ESTIMATE_MIN == 5
    assert NOISE_SIGMA == 0.22
    assert NOISE_CLAMP == (0.6, 1.6)
    assert ANGER_MAX == 100
    assert PREREQ_COUNT == 3


# --- YakState ---------------------------------------------------------------


def test_state_has_exactly_four_fields():
    # Arrange
    state = make_state()

    # Act
    names = tuple(state.__dataclass_fields__)

    # Assert
    assert names == ("root_task", "attempt_count", "seed", "started_at")


def test_attempt_returns_new_state_with_incremented_count():
    # Arrange
    state = make_state(attempt_count=2)

    # Act
    next_state = state.attempt()

    # Assert
    assert next_state.attempt_count == 3
    assert next_state is not state


def test_attempt_does_not_mutate_the_original_state():
    # Arrange
    state = make_state(attempt_count=0)

    # Act
    state.attempt()

    # Assert
    assert state.attempt_count == 0


def test_attempt_keeps_the_other_three_fields():
    # Arrange
    state = make_state()

    # Act
    next_state = state.attempt()

    # Assert
    assert next_state.root_task == state.root_task
    assert next_state.seed == state.seed
    assert next_state.started_at == state.started_at


def test_state_is_frozen():
    # Arrange
    state = make_state()

    # Act / Assert
    with pytest.raises(FrozenInstanceError):
        state.attempt_count = 99  # type: ignore[misc]


# --- leave_time_label -------------------------------------------------------


def test_leave_time_label_at_base_time():
    # Arrange / Act / Assert
    assert leave_time_label(0) == "22:25"


def test_leave_time_label_for_the_initial_estimate():
    # Arrange / Act / Assert
    assert leave_time_label(INITIAL_ESTIMATE_MIN) == "22:30"


def test_leave_time_label_pads_to_two_digits():
    # Arrange / Act / Assert
    assert leave_time_label(40) == "23:05"


# --- texts ------------------------------------------------------------------


def test_templates_are_unique_and_plentiful():
    # Arrange / Act / Assert
    assert len(PREREQUISITE_TEMPLATES) >= 12
    assert len(set(PREREQUISITE_TEMPLATES)) == len(PREREQUISITE_TEMPLATES)


def test_every_template_substitutes_the_task_name():
    # Arrange / Act / Assert
    assert all("{task}" in template for template in PREREQUISITE_TEMPLATES)
    assert all("하기 전에" in template for template in PREREQUISITE_TEMPLATES)


def test_prerequisites_returns_three_distinct_lines_naming_the_task():
    # Arrange
    task = "버튼 색상 변경"

    # Act
    lines = prerequisites_for("test-seed", 1, task)

    # Assert
    assert len(lines) == PREREQ_COUNT
    assert len(set(lines)) == PREREQ_COUNT
    assert all(task in line for line in lines)
    assert all("{task}" not in line for line in lines)


def test_prerequisites_are_pure_for_the_same_seed_and_attempt():
    # Arrange / Act
    first = prerequisites_for("test-seed", 4, "버튼 색상 변경")
    second = prerequisites_for("test-seed", 4, "버튼 색상 변경")

    # Assert
    assert first == second


def test_prerequisites_differ_across_attempts():
    # Arrange / Act
    per_attempt = {prerequisites_for("test-seed", n, "버튼 색상 변경") for n in range(1, 9)}

    # Assert
    assert len(per_attempt) > 1
