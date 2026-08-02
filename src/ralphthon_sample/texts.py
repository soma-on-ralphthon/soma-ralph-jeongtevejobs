"""선행 작업 문구.

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
