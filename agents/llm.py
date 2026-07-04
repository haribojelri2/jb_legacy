"""중앙집중식 LLM 팩토리 — 모델 선택·API 키 검증 단일화.

모든 에이전트는 LLM 클라이언트를 직접 생성하지 않고 get_llm()을 사용한다.
MODEL_SMART / MODEL_FAST 환경변수로 코드 수정 없이 모델 교체 가능.
모델명이 "claude"로 시작하면 Anthropic(Claude), 아니면 OpenAI로 라우팅되므로
.env 한 줄로 제공사 전환·롤백이 가능하다.
"""

import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

# graph 단독 실행·테스트에서도 .env가 로드되도록 모듈 로드 시 1회 수행
# (override=False 기본값 — 이미 설정된 환경변수는 건드리지 않음)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

_DEFAULT_MODELS = {
    "fast":  "claude-opus-4-8",   # 분류·키워드 추출·간단 변환 (비용 절감: MODEL_FAST=claude-haiku-4-5)
    "smart": "claude-opus-4-8",   # 복합 분석·구조화 출력
}

# langchain-anthropic 기본 max_tokens(1024)는 synthesizer 리포트가 잘리므로 넉넉히 지정
_CLAUDE_MAX_TOKENS = 8192


def _configured_models() -> list[str]:
    return [os.getenv(f"MODEL_{t.upper()}", _DEFAULT_MODELS[t]) for t in _DEFAULT_MODELS]


def required_api_keys() -> dict[str, bool]:
    """현재 모델 설정에 실제로 필요한 API 키와 설정 여부를 반환.

    OpenAI: 임베딩(RAG)·STT·TTS에 항상 필요.
    Anthropic: 설정된 모델 중 claude가 하나라도 있으면 필요.
    OpenAI 모델을 tier에 쓰면 그 경우에도 OpenAI 키가 필요(이미 항상 필요이므로 포함).
    """
    models = _configured_models()
    needed = {"OPENAI_API_KEY": True}  # 임베딩·음성 고정 필요
    if any(m.startswith("claude") for m in models):
        needed["ANTHROPIC_API_KEY"] = True
    return {name: bool(os.getenv(name)) for name in needed}


def get_llm(tier: str = "fast", temperature: float = 0.0,
            max_tokens: int | None = None) -> BaseChatModel:
    """tier: "fast" 또는 "smart". MODEL_FAST/MODEL_SMART env로 오버라이드.

    max_tokens: 출력 상한. 중간 산출물(재종합 대상)은 낮게 캡해 지연을 줄인다.
    미지정 시 기본값(_CLAUDE_MAX_TOKENS) — synthesizer 최종 리포트가 잘리지 않도록 넉넉.
    """
    tokens = max_tokens or _CLAUDE_MAX_TOKENS
    model = os.getenv(f"MODEL_{tier.upper()}", _DEFAULT_MODELS[tier])
    if model.startswith("claude"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다. "
                "프로젝트 루트의 .env 파일에 키를 입력해 주세요 (.env.example 참고)."
            )
        # Opus 4.7 이후 모델은 temperature/top_p 파라미터가 제거되어 전달 시 400 에러 — 항상 생략
        # max_retries: 시연장 네트워크 블립(연결 시간 초과) 1~2회에 그래프 전체가 죽지 않도록 방어
        return ChatAnthropic(
            model=model, max_tokens=tokens, api_key=api_key, max_retries=4
        )
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY가 설정되지 않았습니다. "
            "프로젝트 루트의 .env 파일에 키를 입력해 주세요 (.env.example 참고)."
        )
    return ChatOpenAI(model=model, temperature=temperature, api_key=api_key,
                      max_retries=4, max_tokens=tokens)
