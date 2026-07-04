"""금융 파라미터 로더 — config/params.yaml을 앱 구동 시 1회 읽어 전역 제공.

세법·금리·물가 상수를 코드에서 분리한 단일 출처. 세율 개정 등은 params.yaml만
수정하면 되고, 이 모듈이 검증·정규화해 각 계산 모듈에 주입한다.
JB_PARAMS 환경변수로 대체 설정 파일 경로 지정 가능(스테이징/시나리오 A·B 테스트).
"""

import os

import yaml

_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "params.yaml")


def _load() -> dict:
    path = os.getenv("JB_PARAMS", _DEFAULT_PATH)
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise RuntimeError(f"params.yaml 형식 오류: {path}")
    return data


PARAMS: dict = _load()


def brackets(spec: list) -> list[tuple]:
    """YAML의 [상한, 세율, 공제] 리스트를 튜플 리스트로 정규화(.inf 포함)."""
    return [tuple(row) for row in spec]


def get(*keys, default=None):
    """중첩 키 조회 헬퍼: get('monte_carlo', 'seed')."""
    node = PARAMS
    for k in keys:
        if not isinstance(node, dict) or k not in node:
            return default
        node = node[k]
    return node
