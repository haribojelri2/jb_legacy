"""중앙집중식 LLM 팩토리 — 모델 선택·API 키 검증 단일화.

모든 에이전트는 ChatOpenAI를 직접 생성하지 않고 get_llm()을 사용한다.
MODEL_SMART / MODEL_FAST 환경변수로 코드 수정 없이 모델 교체 가능.
"""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# graph 단독 실행·테스트에서도 .env가 로드되도록 모듈 로드 시 1회 수행
# (override=False 기본값 — 이미 설정된 환경변수는 건드리지 않음)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

_DEFAULT_MODELS = {
    "fast":  "gpt-4o-mini",   # 분류·키워드 추출·간단 변환
    "smart": "gpt-4o",        # 복합 분석·구조화 출력
}


def get_llm(tier: str = "fast", temperature: float = 0.0) -> ChatOpenAI:
    """tier: "fast" 또는 "smart". MODEL_FAST/MODEL_SMART env로 오버라이드."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY가 설정되지 않았습니다. "
            "프로젝트 루트의 .env 파일에 키를 입력해 주세요 (.env.example 참고)."
        )
    model = os.getenv(f"MODEL_{tier.upper()}", _DEFAULT_MODELS[tier])
    return ChatOpenAI(model=model, temperature=temperature, api_key=api_key)
