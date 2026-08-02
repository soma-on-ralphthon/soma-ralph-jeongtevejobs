"""테스트 공통 픽스처.

앱의 기본 상태 저장 경로는 실행 디렉터리 기준이다.
격리하지 않으면 테스트가 저장소 루트에 상태 파일을 남기고, 다음 테스트가 그 파일을 복원해
최초 화면 단언이 깨진다. 모든 테스트를 비어 있는 임시 디렉터리에서 돌린다.
"""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """모든 테스트의 작업 디렉터리를 빈 임시 디렉터리로 바꾼다."""
    monkeypatch.chdir(tmp_path)
    return tmp_path
