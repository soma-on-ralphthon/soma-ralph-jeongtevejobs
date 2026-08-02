"""YakState 와 순수 파생 함수.

이 모듈은 Textual 을 import 하지 않는다. 상태 로직을 렌더링 없이 단위 테스트하기 위해서다.
상태는 네 필드뿐이고 나머지는 전부 여기의 순수 함수로 계산한다.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime

from ralphthon_sample.config import BASE_TIME, DEFAULT_SEED

MINUTES_PER_HOUR = 60
MINUTES_PER_DAY = 24 * MINUTES_PER_HOUR


@dataclass(frozen=True, slots=True)
class YakState:
    """한 세션의 전체 상태.

    증가폭, 누적 견적, 분노, 퇴근 시각 표기는 상태가 아니라 (seed, attempt_count) 의 파생값이다.
    RNG 객체를 필드로 들고 있지 않는 이유도 같다. 들고 소비하면 재현이 깨진다.
    """

    root_task: str
    attempt_count: int = 0
    seed: str = DEFAULT_SEED
    started_at: datetime = field(default_factory=datetime.now)

    def attempt(self) -> "YakState":
        """시도 횟수를 하나 올린 새 상태를 반환한다. 기존 객체는 건드리지 않는다."""
        return replace(self, attempt_count=self.attempt_count + 1)


def leave_time_label(total_minutes: int) -> str:
    """기준 시각에 누적 견적을 더한 퇴근 시각을 HH:MM 으로 만든다."""
    base_minutes = BASE_TIME.hour * MINUTES_PER_HOUR + BASE_TIME.minute
    hour, minute = divmod((base_minutes + total_minutes) % MINUTES_PER_DAY, MINUTES_PER_HOUR)
    return f"{hour:02d}:{minute:02d}"
