"""선행 작업 문구, 사과 문구, 성공 확률.

전부 로컬 하드코딩 템플릿이다. LLM 이나 외부 API 를 쓰지 않는다.
문구는 배너 한 줄에 들어가야 하므로 짧게 유지한다.
"""

import random
from dataclasses import dataclass

from ralphthon_sample.config import CATEGORY_PREREQ_COUNT, PREREQ_COUNT

# 어느 카테고리에도 걸리지 않는 입력이 쓰는 범용 풀.
# 카테고리 색이 도는 문구는 전부 아래 카테고리 풀로 옮겼다.
# 여기 남은 것은 무엇을 하려 하든 성립한다.
PREREQUISITE_TEMPLATES: tuple[str, ...] = (
    "{task} 하기 전에 개발 환경 다시 세팅하기",
    "{task} 하기 전에 사내 위키에서 컨벤션 문서 찾기",
    "{task} 하기 전에 레거시 컴포넌트 의존성 파악하기",
    "{task} 하기 전에 패키지 매니저 버전 통일하기",
    "{task} 하기 전에 린트 규칙 팀 합의 받기",
    "{task} 하기 전에 테스트 스냅샷 전부 갱신하기",
    "{task} 하기 전에 기획서 최신 버전 확인하기",
    "{task} 하기 전에 밀린 PR 세 건 먼저 리뷰하기",
    "{task} 하기 전에 사라진 환경 변수 담당자 수소문하기",
    "{task} 하기 전에 사내 계정 권한 다시 신청하기",
    "{task} 하기 전에 지난주 회의록에서 결정사항 찾기",
    "{task} 하기 전에 만료된 사내 인증서 갱신하기",
    "{task} 하기 전에 노트북 디스크 용량 확보하기",
    "{task} 하기 전에 담당자 휴가 복귀일 확인하기",
)


@dataclass(frozen=True, slots=True)
class PrerequisiteCategory:
    """입력 키워드와 그때 나올 선행 작업 풀 한 쌍.

    분류는 전부 로컬 하드코딩이다. LLM 이나 형태소 분석기를 쓰지 않는다.
    """

    name: str
    keywords: tuple[str, ...]
    templates: tuple[str, ...]

    def matches(self, task: str) -> bool:
        """입력에 이 카테고리 키워드가 하나라도 들어 있는지 본다.

        부분 문자열 포함이면 충분하다. 대소문자는 무시한다. `DB` 를 `db` 로 적어도 같은 작업이다.
        """
        lowered = task.casefold()
        return any(keyword.casefold() in lowered for keyword in self.keywords)


UI_CATEGORY = PrerequisiteCategory(
    name="UI",
    keywords=("색상", "버튼", "화면", "폰트", "여백", "컴포넌트", "디자인", "UI"),
    templates=(
        "{task} 하기 전에 디자인 시스템 토큰 정리하기",
        "{task} 하기 전에 접근성 대비 검토 요청하기",
        "{task} 하기 전에 디자인 시스템 변경 승인받기",
        "{task} 하기 전에 피그마 최신 시안과 대조하기",
        "{task} 하기 전에 다크 모드 팔레트 먼저 맞추기",
        "{task} 하기 전에 반응형 기준 폭 합의받기",
    ),
)

DEPLOY_CATEGORY = PrerequisiteCategory(
    name="배포",
    keywords=("배포", "빌드", "파이프라인", "릴리스", "롤백", "도커", "CI"),
    templates=(
        "{task} 하기 전에 CI 캐시 깨진 원인 찾기",
        "{task} 하기 전에 스테이징 재기동 승인받기",
        "{task} 하기 전에 롤백 절차 문서로 남기기",
        "{task} 하기 전에 배포 담당자 슬랙으로 수소문하기",
        "{task} 하기 전에 빌드 아티팩트 서명키 확인하기",
        "{task} 하기 전에 릴리스 노트 초안 먼저 쓰기",
    ),
)

DATA_CATEGORY = PrerequisiteCategory(
    name="데이터",
    keywords=("마이그레이션", "쿼리", "스키마", "인덱스", "테이블", "데이터베이스", "DB"),
    templates=(
        "{task} 하기 전에 로컬 DB 마이그레이션 되살리기",
        "{task} 하기 전에 마이그레이션 순서 합의받기",
        "{task} 하기 전에 운영 백업 복구되는지 확인하기",
        "{task} 하기 전에 느린 쿼리 실행 계획 뜯어보기",
        "{task} 하기 전에 인덱스 재생성 시간 산정하기",
        "{task} 하기 전에 스키마 변경 리뷰 요청하기",
    ),
)

# 판정 순서다. 두 카테고리에 동시에 걸리면 먼저 선언된 쪽이 이긴다.
CATEGORIES: tuple[PrerequisiteCategory, ...] = (UI_CATEGORY, DEPLOY_CATEGORY, DATA_CATEGORY)


def category_for(task: str) -> PrerequisiteCategory | None:
    """입력이 걸리는 카테고리. 어디에도 안 걸리면 None 이고 범용 풀만 쓴다."""
    for category in CATEGORIES:
        if category.matches(task):
            return category
    return None


def prerequisites_for(seed: str, attempt_count: int, task: str) -> tuple[str, ...]:
    """해당 회차의 선행 작업 문구를 중복 없이 PREREQ_COUNT 개 뽑는다.

    (seed, task, attempt_count) 만으로 결정되는 순수 함수다.
    task 를 시드에 넣지 않으면 무엇을 입력하든 이름만 바뀐 같은 문구가 나와 두 번만에 들통난다.
    RNG 를 들고 다니지 않고 매번 새로 만들어야 회귀 테스트가 재현된다.
    """
    rng = random.Random(f"{seed}:{task}:{attempt_count}")
    category = category_for(task)
    if category is None:
        picked = rng.sample(PREREQUISITE_TEMPLATES, PREREQ_COUNT)
    else:
        # 관련 문구 2개에 엉뚱한 것 1개를 섞는다. 풀이 서로 겹치지 않아 중복은 생기지 않는다.
        picked = rng.sample(category.templates, CATEGORY_PREREQ_COUNT)
        picked += rng.sample(PREREQUISITE_TEMPLATES, PREREQ_COUNT - CATEGORY_PREREQ_COUNT)
        # 엉뚱한 것이 늘 마지막 줄이면 그 자체가 규칙으로 읽힌다.
        rng.shuffle(picked)

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
