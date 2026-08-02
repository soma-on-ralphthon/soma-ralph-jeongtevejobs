"""상태 스냅샷의 저장과 복원.

state.py 와 마찬가지로 Textual 을 import 하지 않는다. 파일 입출력과 경계 검증만 담당한다.
저장하는 값은 상태 네 필드뿐이다. 트리와 파생값은 (seed, attempt_count) 로 전부 재계산된다.
파생값을 파일에 남기면 수치 모델이 바뀔 때 화면과 파일이 어긋난다.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ralphthon_sample.config import STATE_FILENAME
from ralphthon_sample.state import YakState

# TUI 가 떠 있는 동안 stderr 로 로그가 새면 화면이 깨진다.
# 기록은 남기되 어디에 출력할지는 앱을 띄우는 쪽이 정하게 NullHandler 를 달아둔다.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

MIN_ATTEMPT_COUNT = 0
JSON_INDENT = 2


def default_state_path() -> Path:
    """기본 저장 경로. 프로젝트 루트에서 실행한다는 전제다."""
    return Path.cwd() / STATE_FILENAME


def save_state(state: YakState, path: Path) -> None:
    """상태 네 필드를 JSON 으로 덮어쓴다.

    쓰기 실패는 여기서 숨기지 않고 그대로 올린다. 저장은 부가 기능이므로
    앱이 그 예외를 받아 로그만 남기고 계속 굴러간다.
    """
    payload = {
        "root_task": state.root_task,
        "attempt_count": state.attempt_count,
        "seed": state.seed,
        "started_at": state.started_at.isoformat(),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=JSON_INDENT),
        encoding="utf-8",
    )


def load_state(path: Path) -> YakState | None:
    """저장된 상태를 읽는다. 없거나 깨졌으면 None 이다.

    조용히 새 상태로 시작하되 예외를 삼키지는 않는다. 이유는 로그로 남긴다.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.debug("저장된 상태가 없다: %s", path)
        return None
    except OSError:
        logger.warning("상태 파일을 읽지 못했다: %s", path, exc_info=True)
        return None

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("상태 파일이 올바른 JSON 이 아니다: %s", path, exc_info=True)
        return None

    try:
        return _parse_state(payload)
    except (KeyError, TypeError, ValueError) as error:
        logger.warning("상태 파일의 내용이 유효하지 않다: %s (%r)", path, error)
        return None


def _parse_state(payload: Any) -> YakState:
    """외부 입력을 상태로 바꾼다.

    사람이 손댈 수 있는 파일이라 네 필드를 전부 경계에서 검증한다.
    값이 조금이라도 이상하면 복원하지 않고 새 상태로 시작하는 편이 낫다.
    """
    if not isinstance(payload, dict):
        raise TypeError("최상위 값이 객체가 아니다")

    return YakState(
        root_task=_as_task(payload["root_task"]),
        attempt_count=_as_attempt_count(payload["attempt_count"]),
        seed=_as_seed(payload["seed"]),
        started_at=_as_started_at(payload["started_at"]),
    )


def _as_task(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"root_task 가 비어 있거나 문자열이 아니다: {value!r}")
    return value


def _as_attempt_count(value: Any) -> int:
    # bool 은 int 의 하위 타입이라 isinstance 만으로는 걸러지지 않는다.
    if isinstance(value, bool) or not isinstance(value, int) or value < MIN_ATTEMPT_COUNT:
        raise ValueError(f"attempt_count 가 0 이상의 정수가 아니다: {value!r}")
    return value


def _as_seed(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f"seed 가 문자열이 아니다: {value!r}")
    return value


def _as_started_at(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"started_at 이 문자열이 아니다: {value!r}")
    # 형식이 틀리면 fromisoformat 이 ValueError 를 낸다.
    return datetime.fromisoformat(value)
