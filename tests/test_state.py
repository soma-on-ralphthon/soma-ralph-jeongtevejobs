"""순수 함수와 상태 단위 테스트.

여기서는 Textual 을 import 하지 않는다. state.py 와 texts.py 는 렌더링과 무관해야 한다.
"""

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from ralphthon_sample.config import (
    ANGER_MAX,
    BASE_TIME,
    DEMO_SEED,
    INITIAL_ESTIMATE_MIN,
    NOISE_CLAMP,
    NOISE_SIGMA,
    PREREQ_COUNT,
    QUIT_SEQUENCE_LENGTH,
    QUIT_WINDOW_SEC,
    SLUMP_ATTEMPT,
    SLUMP_RATIO,
)
from ralphthon_sample.state import (
    YakState,
    added_minutes,
    anger,
    anger_for_added_minutes,
    fib,
    increment,
    leave_label,
    leave_time_label,
    mult,
    next_quit_press,
    total_minutes,
)
from ralphthon_sample.texts import (
    APOLOGIES,
    PREREQUISITE_TEMPLATES,
    apology_for,
    hope_line,
    hope_rate,
    prerequisites_for,
)

FIXED_STARTED_AT = datetime(2026, 8, 2, 22, 25)

# 속성 테스트용 임의 seed. 특정 seed 에만 성립하는 성질을 걸러내려고 넉넉히 잡는다.
SAMPLE_SEEDS = tuple(f"seed-{index}" for index in range(40))

# 분노가 반드시 100 에 닿아야 하는 회차 구간. PRODUCT.md 의 "7~9회차 안에 도달".
ANGER_MAX_EARLIEST_ATTEMPT = 7
ANGER_MAX_LATEST_ATTEMPT = 9

# DEMO_SEED 의 실제 1~8회차 증가폭. 탐색으로 한 번 구해 잠갔다.
# 이 값이 깨지면 DEMO_SEED 나 수치 모델이 바뀐 것이다.
# 기댓값 3, 5, 8, 13, 21, 18, 55, 89 와 다른 것은 정상이다. 노이즈가 seed 마다 다르다.
DEMO_SEED_INCREMENTS = (3, 5, 7, 11, 21, 18, 43, 98)


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


def test_leave_time_label_marks_the_next_day_after_midnight():
    # Arrange / Act / Assert
    # 22:25 + 95분 = 정확히 자정. 여기서 "익일"이 붙기 시작한다.
    assert leave_time_label(95) == "익일 00:00"
    assert leave_time_label(128) == "익일 00:33"


def test_leave_time_label_does_not_silently_wrap_past_midnight():
    # Arrange / Act / Assert
    # % MINUTES_PER_DAY 로 조용히 감싸면 7회차 클라이맥스가 사라진다.
    assert leave_time_label(94) == "23:59"
    assert leave_time_label(96) != "00:01"


# --- 수치 모델: fib / mult / increment ---------------------------------------


def test_fib_starts_at_three_and_five():
    # Arrange / Act
    sequence = tuple(fib(n) for n in range(1, 10))

    # Assert
    assert sequence == (3, 5, 8, 13, 21, 34, 55, 89, 144)


def test_fib_rejects_attempt_numbers_below_one():
    # Arrange / Act / Assert
    with pytest.raises(ValueError):
        fib(0)


def test_mult_stays_inside_the_noise_clamp():
    # Arrange
    low, high = NOISE_CLAMP

    # Act
    values = [mult(seed, n) for seed in SAMPLE_SEEDS for n in range(1, 10)]

    # Assert
    assert all(low <= value <= high for value in values)


def test_mult_is_pure_for_the_same_seed_and_attempt():
    # Arrange / Act
    first = mult("test-seed", 3)
    second = mult("test-seed", 3)

    # Assert
    # RNG 를 상태로 들고 소비하면 두 번째 호출이 달라진다. 회귀 테스트가 재현되지 않는다.
    assert first == second


def test_every_increment_is_positive():
    # Arrange / Act
    increments = [increment(seed, n) for seed in SAMPLE_SEEDS for n in range(1, 10)]

    # Assert
    assert all(value > 0 for value in increments)


def test_sixth_increment_is_a_forced_slump_for_every_seed():
    # Arrange / Act / Assert
    # 6회차 하락만 전체 seed 에서 보장된다. 나머지 회차의 단조 증가는 DEMO_SEED 에서만 본다.
    for seed in SAMPLE_SEEDS:
        assert increment(seed, SLUMP_ATTEMPT) < increment(seed, SLUMP_ATTEMPT - 1)


def test_sixth_increment_derives_from_the_fifth_not_from_its_own_noise():
    # Arrange / Act / Assert
    # mult(seed, 6) 을 계산하면 이 등식이 깨진다.
    for seed in SAMPLE_SEEDS:
        expected = max(1, round(increment(seed, SLUMP_ATTEMPT - 1) * SLUMP_RATIO))
        assert increment(seed, SLUMP_ATTEMPT) == expected


# --- 수치 모델: total_minutes / anger ----------------------------------------


def test_total_minutes_starts_at_the_initial_estimate():
    # Arrange / Act / Assert
    assert total_minutes("test-seed", 0) == INITIAL_ESTIMATE_MIN
    assert added_minutes("test-seed", 0) == 0


def test_total_minutes_is_strictly_increasing():
    # Arrange / Act / Assert
    for seed in SAMPLE_SEEDS:
        totals = [total_minutes(seed, n) for n in range(0, 10)]
        assert all(later > earlier for earlier, later in zip(totals, totals[1:], strict=False))


@pytest.mark.parametrize(
    ("added", "expected"),
    [(15, 11), (35, 25), (55, 39), (75, 53), (95, 67), (115, 81), (135, 95)],
)
def test_anger_rounds_half_up_with_integer_arithmetic(added: int, expected: int):
    # Arrange / Act / Assert
    # 부동소수점 round() 는 banker's rounding 때문에 이 값들에서 1 씩 작게 나온다.
    assert anger_for_added_minutes(added) == expected


def test_anger_matches_the_reference_flow_of_the_product_spec():
    # Arrange
    # PRODUCT.md 기준 흐름의 누적 추가분과 분노.
    reference = {3: 2, 8: 6, 16: 11, 29: 20, 50: 35, 68: 48, 123: 86}

    # Act / Assert
    assert all(anger_for_added_minutes(added) == value for added, value in reference.items())


def test_anger_is_capped_at_the_maximum():
    # Arrange / Act / Assert
    assert anger_for_added_minutes(212) == ANGER_MAX
    assert anger_for_added_minutes(10_000) == ANGER_MAX


def test_anger_reaches_the_maximum_between_the_seventh_and_ninth_attempt():
    # Arrange / Act / Assert
    for seed in SAMPLE_SEEDS:
        angers = [anger(seed, n) for n in range(0, ANGER_MAX_LATEST_ATTEMPT + 1)]
        first_max = next(n for n, value in enumerate(angers) if value == ANGER_MAX)
        assert ANGER_MAX_EARLIEST_ATTEMPT <= first_max <= ANGER_MAX_LATEST_ATTEMPT


def test_leave_label_is_undecided_exactly_when_anger_is_maxed():
    # Arrange / Act / Assert
    for seed in SAMPLE_SEEDS:
        for n in range(0, ANGER_MAX_LATEST_ATTEMPT + 1):
            is_maxed = anger(seed, n) == ANGER_MAX
            assert (leave_label(seed, n) == "미정") is is_maxed


def test_leave_label_shows_the_clock_before_anger_is_maxed():
    # Arrange / Act / Assert
    assert leave_label(DEMO_SEED, 0) == "22:30"


# --- DEMO_SEED --------------------------------------------------------------


def test_demo_seed_increments_strictly_increase_through_the_fifth_attempt():
    # Arrange / Act
    increments = [increment(DEMO_SEED, n) for n in range(1, 6)]

    # Assert
    assert all(later > earlier for earlier, later in zip(increments, increments[1:], strict=False))


def test_demo_seed_seventh_attempt_lands_in_the_required_window():
    # Arrange / Act
    added = added_minutes(DEMO_SEED, 7)

    # Assert
    # 90 이상이라야 자정을 넘고, 142 이하라야 분노가 아직 100 미만이다.
    assert 90 <= added <= 142


def test_demo_seed_seventh_attempt_crosses_midnight_with_anger_below_max():
    # Arrange / Act
    label = leave_label(DEMO_SEED, 7)

    # Assert
    assert label.startswith("익일")
    assert anger(DEMO_SEED, 7) < ANGER_MAX


def test_demo_seed_eighth_attempt_maxes_anger_and_gives_up_on_the_clock():
    # Arrange / Act / Assert
    assert anger(DEMO_SEED, 8) == ANGER_MAX
    assert leave_label(DEMO_SEED, 8) == "미정"


def test_demo_seed_increment_sequence_is_locked():
    # Arrange / Act
    increments = tuple(increment(DEMO_SEED, n) for n in range(1, 9))

    # Assert
    # 회귀 잠금. DEMO_SEED 나 수치 모델이 바뀌면 여기서 먼저 깨진다.
    assert increments == DEMO_SEED_INCREMENTS


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


# --- 사과 문구 ---------------------------------------------------------------


def test_apology_table_matches_the_product_spec():
    # Arrange
    expected = (
        "일정 변경 안내드립니다. 불편을 드려 죄송합니다.",
        "일정이 조정되었습니다. 죄송합니다.",
        "죄송합니다.",
        "죄송",
        "ㅈㅅ",
    )

    # Act
    actual = APOLOGIES

    # Assert
    assert actual == expected
    assert all(apology_for(n) == expected[n - 1] for n in range(1, 6))


def test_apologies_get_shorter_every_attempt():
    # Arrange / Act
    lengths = [len(text) for text in APOLOGIES]

    # Assert
    # "죄송"과 "ㅈㅅ"은 둘 다 두 글자다. 길이는 줄기만 하고 늘지 않는다.
    assert all(later <= earlier for earlier, later in zip(lengths, lengths[1:], strict=False))
    assert lengths[-1] < lengths[0]


def test_apology_disappears_from_the_sixth_attempt():
    # Arrange / Act / Assert
    assert apology_for(6) is None
    assert apology_for(7) is None
    assert apology_for(99) is None


def test_apology_is_absent_before_the_first_attempt():
    # Arrange / Act / Assert
    assert apology_for(0) is None


# --- 성공 확률 ---------------------------------------------------------------


def test_hope_rate_is_indexed_from_zero():
    # Arrange / Act
    rates = [hope_rate(n) for n in range(0, 9)]

    # Assert
    # hope_rate(0) 이 아직 한 번도 시도하지 않은 최초 화면의 값이다.
    assert rates == [97, 94, 89, 81, 70, 56, 39, 21, 3]


def test_hope_rate_is_zero_from_the_ninth_attempt():
    # Arrange / Act / Assert
    assert hope_rate(9) == 0
    assert hope_rate(50) == 0


def test_hope_rate_never_increases():
    # Arrange / Act
    rates = [hope_rate(n) for n in range(0, 12)]

    # Assert
    assert all(later <= earlier for earlier, later in zip(rates, rates[1:], strict=False))


def test_hope_line_shows_the_next_attempts_rate():
    # Arrange / Act
    line = hope_line(0)

    # Assert
    assert "97%" in line
    assert "재시도" in line


# --- 종료 시퀀스 시간창 -------------------------------------------------------
#
# 시간창 판정은 주입 clock 이 준 값만 보는 순수 함수다.
# time.monotonic 을 전역 monkeypatch 하면 Textual timer 와 Toast 가 오염된다.


def test_first_quit_press_opens_a_sequence():
    # Arrange / Act
    pressed = next_quit_press(0, None, now=10.0, window=QUIT_WINDOW_SEC)

    # Assert
    assert pressed == 1


def test_quit_press_inside_the_window_advances_the_counter():
    # Arrange / Act
    pressed = next_quit_press(1, 10.0, now=11.4, window=QUIT_WINDOW_SEC)

    # Assert
    assert pressed == 2


def test_quit_press_exactly_on_the_window_edge_still_counts():
    # Arrange / Act
    pressed = next_quit_press(1, 10.0, now=10.0 + QUIT_WINDOW_SEC, window=QUIT_WINDOW_SEC)

    # Assert
    assert pressed == 2


def test_quit_press_after_the_window_opens_a_new_sequence():
    # Arrange / Act
    pressed = next_quit_press(2, 10.0, now=10.0 + QUIT_WINDOW_SEC + 0.01, window=QUIT_WINDOW_SEC)

    # Assert
    # 리셋 후의 Ctrl+C 는 새 시퀀스다. 그래서 선행 작업 3개가 다시 붙는다.
    assert pressed == 1


def test_three_quit_presses_inside_the_window_reach_the_sequence_length():
    # Arrange
    previous_press, previous_at = 0, None

    # Act
    presses = []
    for tick in (10.0, 10.5, 11.0):
        previous_press = next_quit_press(
            previous_press, previous_at, now=tick, window=QUIT_WINDOW_SEC
        )
        previous_at = tick
        presses.append(previous_press)

    # Assert
    assert presses == [1, 2, QUIT_SEQUENCE_LENGTH]
