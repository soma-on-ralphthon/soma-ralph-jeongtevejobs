"""상수 전용 모듈.

수치의 근거는 PRODUCT.md 의 수치 모델이다. 여기 없는 값을 코드에 직접 박지 마라.
"""

from datetime import time

# 퇴근 시간 계산의 기준 시각. "이미 밤 10시가 넘었다"는 전제를 만든다.
BASE_TIME = time(22, 25)

# 낙관적인 최초 견적. 모든 배신은 이 5분에서 출발한다.
INITIAL_ESTIMATE_MIN = 5

# 증가폭 노이즈. mult(seed, n) = clamp(gauss(1.0, NOISE_SIGMA), *NOISE_CLAMP)
NOISE_SIGMA = 0.22
NOISE_CLAMP = (0.6, 1.6)

# 증가폭의 뼈대. 3, 5 에서 시작하는 무한 재귀 수열 (3, 5, 8, 13, 21, 34, 55, 89, 144, ...)
FIB_START = (3, 5)

# 가짜 안도를 만드는 회차. 이 회차만 자기 노이즈를 계산하지 않고 직전 증가폭을 깎는다.
# 여기서 한 번 줄여둬야 7회차 폭증이 배신으로 느껴진다.
SLUMP_ATTEMPT = 6
SLUMP_RATIO = 0.85

# 분노 게이지 상한. 여기에 닿으면 퇴근 시각이 "미정"이 된다.
ANGER_MAX = 100

# 분노는 정수 산술이다. min(ANGER_MAX, (7 * 추가분 + 5) // 10)
# 부동소수점 round() 는 banker's rounding 때문에 추가분 15·35·55·75·95·115·135 에서 다른 값을 낸다.
ANGER_PER_MINUTE_NUMERATOR = 7
ANGER_PER_MINUTE_DENOMINATOR = 10
ANGER_HALF_UP_OFFSET = 5

# 퇴근 시각 표기. 분노가 상한이면 숫자를 포기하고, 자정을 넘기면 접두어를 붙인다.
UNKNOWN_LEAVE_LABEL = "미정"
NEXT_DAY_PREFIX = "익일"

# attempt 한 번이 만들어내는 선행 작업 개수.
PREREQ_COUNT = 3

# 입력이 카테고리에 걸렸을 때 그 카테고리 풀에서 뽑는 개수. 나머지는 범용 풀에서 채운다.
# 셋 다 관련 문구면 농담이 아니라 진짜 할 일 목록처럼 보인다. 한 개는 엉뚱해야 야크 셰이빙이 된다.
CATEGORY_PREREQ_COUNT = 2

# 사과 Toast 표시 시간(초). 사과는 짧게 지나가야 한다.
APOLOGY_TIMEOUT_SEC = 1.0

# 트리 들여쓰기 폭. 무한 후퇴가 깊어져도 80칸 안에 남아야 한다.
TREE_GUIDE_DEPTH = 2

# 종료 시퀀스. 첫 키가 attempt 를 만들고, 시간창 안에 이 횟수를 채워야 빠져나갈 수 있다.
# 시간창을 넘기면 카운터가 리셋되고, 다음 키는 새 시퀀스의 첫 키라 선행 작업이 또 붙는다.
QUIT_SEQUENCE_LENGTH = 3
QUIT_WINDOW_SEC = 1.5

# 배너 높이(행). 콘텐츠 6행(카운터 1 + 선행 작업 3 + 분노 변화 1 + 누적 변화 1) + 하단 border 1행.
QUIT_BANNER_HEIGHT = 7

# 상태 저장 파일 이름. 프로젝트 루트에 두고 .gitignore 로 제외한다.
# 저장하는 값은 상태 네 필드뿐이다. 트리와 파생값은 전부 재계산으로 복원된다.
STATE_FILENAME = ".ralphthon-state.json"

# 데모 기본 seed.
#
# 고정된 유한 범위 str(0..9999) 에서 아래 두 조건을 만족하는 가장 작은 값을 한 번 탐색해 박았다.
#   조건 1  1~5회차 증가폭이 엄격히 증가
#   조건 2  7회차 누적 추가분이 90 이상 142 이하
#           90 이상   22:25 + 5 + 추가분이 자정을 넘어 "익일"이 표시된다
#           142 이하  분노가 아직 100 미만이라 "미정"에 가려지지 않는다
# 탐색 로직은 제품 코드에 남기지 않는다. 결과는 tests/test_state.py 가 회귀로 잠근다.
DEMO_SEED = "0"
