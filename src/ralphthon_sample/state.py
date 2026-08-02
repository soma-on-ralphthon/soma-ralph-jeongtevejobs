"""YakState 와 순수 파생 함수.

이 모듈은 Textual 을 import 하지 않는다. 상태 로직을 렌더링 없이 단위 테스트하기 위해서다.
상태는 네 필드뿐이고 나머지는 전부 여기의 순수 함수로 계산한다.
"""

import random
from dataclasses import dataclass, field, replace
from datetime import datetime

from ralphthon_sample.config import (
    ANGER_HALF_UP_OFFSET,
    ANGER_MAX,
    ANGER_PER_MINUTE_DENOMINATOR,
    ANGER_PER_MINUTE_NUMERATOR,
    BASE_TIME,
    DEMO_SEED,
    FIB_START,
    INITIAL_ESTIMATE_MIN,
    NEXT_DAY_PREFIX,
    NOISE_CLAMP,
    NOISE_SIGMA,
    SLUMP_ATTEMPT,
    SLUMP_RATIO,
    STALLED_LABEL,
    UNKNOWN_LEAVE_LABEL,
)

MINUTES_PER_HOUR = 60
MINUTES_PER_DAY = 24 * MINUTES_PER_HOUR
SECONDS_PER_MINUTE = 60

# 증가폭 하한. 노이즈가 아무리 낮아도 0분짜리 야크는 없다.
MIN_INCREMENT = 1

# 남은 시간의 바닥. 견적이 음수로 내려가는 대신 여기서 멈춘다.
NO_REMAINING_SECONDS = 0


@dataclass(frozen=True, slots=True)
class YakState:
    """한 세션의 전체 상태.

    증가폭, 누적 견적, 분노, 퇴근 시각 표기는 상태가 아니라 (seed, attempt_count) 의 파생값이다.
    RNG 객체를 필드로 들고 있지 않는 이유도 같다. 들고 소비하면 재현이 깨진다.
    """

    root_task: str
    attempt_count: int = 0
    seed: str = DEMO_SEED
    started_at: datetime = field(default_factory=datetime.now)

    def attempt(self) -> "YakState":
        """시도 횟수를 하나 올린 새 상태를 반환한다. 기존 객체는 건드리지 않는다."""
        return replace(self, attempt_count=self.attempt_count + 1)


def fib(attempt_count: int) -> int:
    """증가폭의 뼈대. fib(1) == 3, fib(2) == 5, fib(3) == 8 ...

    회차는 1부터 색인한다. 재귀 대신 누적으로 계산해 깊은 회차에서도 스택이 터지지 않는다.
    """
    if attempt_count < 1:
        raise ValueError(f"회차는 1부터 색인한다: {attempt_count}")

    previous, current = FIB_START
    for _ in range(attempt_count - 1):
        previous, current = current, previous + current
    return previous


def mult(seed: str, attempt_count: int) -> float:
    """해당 회차의 노이즈 배율. clamp(gauss(1.0, NOISE_SIGMA), *NOISE_CLAMP).

    RNG 를 들고 다니지 않고 회차마다 새로 만들어야 순수 함수가 되고 회귀 테스트가 재현된다.
    """
    low, high = NOISE_CLAMP
    raw = random.Random(f"{seed}:{attempt_count}").gauss(1.0, NOISE_SIGMA)
    return min(max(raw, low), high)


def increment(seed: str, attempt_count: int) -> int:
    """해당 회차에 늘어나는 견적(분).

    SLUMP_ATTEMPT 회차만 예외다. 자기 노이즈를 계산하지 않고 직전 증가폭을 깎아 가짜 안도를 만든다.
    여기서 mult(seed, SLUMP_ATTEMPT) 를 부르면 전체 seed 하락 보장이 깨진다.
    """
    if attempt_count == SLUMP_ATTEMPT:
        slumped = increment(seed, SLUMP_ATTEMPT - 1) * SLUMP_RATIO
        return max(MIN_INCREMENT, round(slumped))

    return max(MIN_INCREMENT, round(fib(attempt_count) * mult(seed, attempt_count)))


def added_minutes(seed: str, attempt_count: int) -> int:
    """최초 견적 대비 늘어난 분. 분노는 이 값만 본다."""
    return sum(increment(seed, n) for n in range(1, attempt_count + 1))


def total_minutes(seed: str, attempt_count: int) -> int:
    """최초 견적에 그때까지의 증가폭을 전부 더한 누적 견적(분)."""
    return INITIAL_ESTIMATE_MIN + added_minutes(seed, attempt_count)


def anger_for_added_minutes(added: int) -> int:
    """추가분을 분노로 바꾼다. 정수 산술 half-up 이다.

    부동소수점 round() 를 쓰면 banker's rounding 때문에
    추가분 15·35·55·75·95·115·135 에서 1 씩 작은 값이 나온다.
    """
    scaled = ANGER_PER_MINUTE_NUMERATOR * added + ANGER_HALF_UP_OFFSET
    return min(ANGER_MAX, scaled // ANGER_PER_MINUTE_DENOMINATOR)


def anger(seed: str, attempt_count: int) -> int:
    """해당 회차의 분노. 최초 견적 대비 배신 배율에 비례하고 ANGER_MAX 에서 고정된다."""
    return anger_for_added_minutes(added_minutes(seed, attempt_count))


def leave_time_label(total_minutes_value: int) -> str:
    """기준 시각에 누적 견적을 더한 퇴근 시각을 HH:MM 으로 만든다.

    자정을 넘기면 접두어를 붙인다. 하루로 조용히 감싸면 7회차 클라이맥스가 사라진다.
    """
    base_minutes = BASE_TIME.hour * MINUTES_PER_HOUR + BASE_TIME.minute
    day_offset, minute_of_day = divmod(base_minutes + total_minutes_value, MINUTES_PER_DAY)
    hour, minute = divmod(minute_of_day, MINUTES_PER_HOUR)

    clock = f"{hour:02d}:{minute:02d}"
    if day_offset == 0:
        return clock
    return f"{NEXT_DAY_PREFIX} {clock}"


def remaining_seconds(seed: str, attempt_count: int, elapsed_seconds: float) -> int:
    """이번 회차의 누적 견적에서 흘러간 만큼을 뺀 남은 시간(초).

    경과 시간을 인자로 받는다. 함수 안에서 시계를 읽으면 순수하지 않아 재현되지 않는다.
    총량은 attempt 가 정하고 줄어드는 속도만 시계가 정한다. 회차가 오르면 남은 시간이 튀어오른다.
    소수점은 버린다. 0.9 초는 아직 1 초가 지난 것이 아니다.
    """
    total = total_minutes(seed, attempt_count) * SECONDS_PER_MINUTE
    return max(NO_REMAINING_SECONDS, total - int(elapsed_seconds))


def remaining_label(remaining: int) -> str:
    """남은 시간 표기. 1분 미만이면 초만 쓴다.

    바닥에 닿으면 STALLED_LABEL 로 고정된다. 완료 개념이 없으니 0초를 완료로 읽히게 두지 않는다.
    """
    if remaining <= NO_REMAINING_SECONDS:
        return STALLED_LABEL

    minutes, seconds = divmod(remaining, SECONDS_PER_MINUTE)
    if minutes == 0:
        return f"{seconds}초"
    return f"{minutes}분 {seconds}초"


def leave_label(seed: str, attempt_count: int) -> str:
    """화면에 띄울 퇴근 시각 표기. 분노가 상한이면 숫자를 포기한다."""
    if anger(seed, attempt_count) >= ANGER_MAX:
        return UNKNOWN_LEAVE_LABEL
    return leave_time_label(total_minutes(seed, attempt_count))


def next_quit_press(
    previous_press: int,
    previous_at: float | None,
    now: float,
    window: float,
) -> int:
    """이번 종료 키가 시퀀스의 몇 번째인지 판정한다.

    직전 키가 없거나 시간창을 넘겼으면 새 시퀀스의 첫 키다.
    시각은 App 이 주입한 clock 이 준다. time.monotonic 을 전역 monkeypatch 하면
    Textual timer 와 Toast 가 오염되므로 여기서는 숫자만 받는다.
    """
    if previous_press < 1 or previous_at is None or now - previous_at > window:
        return 1
    return previous_press + 1
