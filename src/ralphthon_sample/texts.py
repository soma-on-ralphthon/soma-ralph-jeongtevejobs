"""선행 작업 문구, 사과 문구, 성공 확률.

전부 로컬 하드코딩 템플릿이다. LLM 이나 외부 API 를 쓰지 않는다.
문구는 배너 한 줄에 들어가야 하므로 짧게 유지한다.
"""

import random

from ralphthon_sample.config import PREREQ_COUNT

PREREQUISITE_TEMPLATES: tuple[str, ...] = (
    "{task} 하기 전에 개발 환경 다시 세팅하기",
    "{task} 하기 전에 디자인 시스템 토큰 정리하기",
    "{task} 하기 전에 사내 위키에서 컨벤션 문서 찾기",
    "{task} 하기 전에 레거시 컴포넌트 의존성 파악하기",
    "{task} 하기 전에 패키지 매니저 버전 통일하기",
    "{task} 하기 전에 CI 캐시 깨진 원인 찾기",
    "{task} 하기 전에 린트 규칙 팀 합의 받기",
    "{task} 하기 전에 테스트 스냅샷 전부 갱신하기",
    "{task} 하기 전에 스테이징 재기동 승인받기",
    "{task} 하기 전에 접근성 대비 검토 요청하기",
    "{task} 하기 전에 기획서 최신 버전 확인하기",
    "{task} 하기 전에 밀린 PR 세 건 먼저 리뷰하기",
    "{task} 하기 전에 로컬 DB 마이그레이션 되살리기",
    "{task} 하기 전에 사라진 환경 변수 담당자 수소문하기",
)


def prerequisites_for(seed: str, attempt_count: int, task: str) -> tuple[str, ...]:
    """해당 회차의 선행 작업 문구를 중복 없이 PREREQ_COUNT 개 뽑는다.

    (seed, attempt_count) 만으로 결정되는 순수 함수다.
    RNG 를 들고 다니지 않고 회차마다 새로 만들어야 회귀 테스트가 재현된다.
    """
    rng = random.Random(f"{seed}:{attempt_count}")
    picked = rng.sample(PREREQUISITE_TEMPLATES, PREREQ_COUNT)
    return tuple(template.format(task=task) for template in picked)


# 회차마다 짧아지는 사과. 성의가 빠지는 속도가 곧 배신의 크기다.
# 6회차부터는 사과 자체가 사라진다.
APOLOGIES: tuple[str, ...] = (
    "일정 변경 안내드립니다. 불편을 드려 죄송합니다.",
    "일정이 조정되었습니다. 죄송합니다.",
    "죄송합니다.",
    "죄송",
    "ㅈㅅ",
)

# 다음 재시도의 성공 확률. attempt_count 로 색인하고 0 부터 시작한다.
# 1 부터 색인하면 아직 시도하지 않은 최초 화면에 표시할 값이 없어진다.
HOPE_RATES: tuple[int, ...] = (97, 94, 89, 81, 70, 56, 39, 21, 3)

# 거짓 희망. 남은 차단 작업은 무슨 일이 있어도 1개다.
BLOCKED_LABEL = "남은 차단 작업: 1개"


def apology_for(attempt_count: int) -> str | None:
    """해당 회차의 사과 문구. 사과가 없는 회차는 None 이다."""
    if 1 <= attempt_count <= len(APOLOGIES):
        return APOLOGIES[attempt_count - 1]
    return None


def hope_rate(attempt_count: int) -> int:
    """다음 재시도의 성공 확률(%). 표를 넘어가면 0 이다."""
    if 0 <= attempt_count < len(HOPE_RATES):
        return HOPE_RATES[attempt_count]
    return 0


def hope_line(attempt_count: int) -> str:
    """거짓 희망 한 줄. 다음 재시도의 성공 확률을 붙인다."""
    return f"원래 작업 재시도 — 성공 확률 {hope_rate(attempt_count)}%"
