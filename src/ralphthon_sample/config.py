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

# 분노 게이지 상한. 여기에 닿으면 퇴근 시각이 "미정"이 된다.
ANGER_MAX = 100

# attempt 한 번이 만들어내는 선행 작업 개수.
PREREQ_COUNT = 3

# 세션 기본 seed. 데모용 고정 seed 는 core 2 에서 별도로 정한다.
DEFAULT_SEED = "ralphthon"
