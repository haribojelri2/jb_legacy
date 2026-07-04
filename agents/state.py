from typing import Annotated
from typing_extensions import TypedDict
import operator


class AgentState(TypedDict):
    messages: Annotated[list[dict], operator.add]
    user_id: str
    query: str
    route: str  # valuation | tax | post_exit | family | general (레거시 호환)
    selected_agents: list[str]  # Supervisor가 동적으로 결정한 투입 에이전트 목록

    # Profiler
    user_profile: dict

    # Business Valuation Agent
    business_valuation: dict

    # Tax & Succession Agent (RAG)
    tax_comparison: dict      # {"sale": {...}, "succession": {...}}
    tax_rag_context: str

    # Post-Exit WM Agent
    retirement_portfolio: dict

    # Family Bridge
    family_notified: bool
    family_message: str

    # Compliance
    compliance_passed: bool
    compliance_feedback: str
    retry_count: int

    # GAN 적대 검증 (GAN_AUTO=1일 때 그래프 내 자동 실행)
    gan_score: int
    gan_verdict: str        # 통과 | 조건부통과 | 재생성필요 | ""
    gan_regen_needed: bool  # True면 synthesizer 재생성으로 라우팅
    gan_retry_count: int    # GAN 기반 재생성 횟수 (최대 1회)

    # Clarification (추가 질문)
    clarification_needed: str   # 비어있으면 추가 질문 불필요
    clarification_answer: str   # 사용자 답변

    # 사용자 입력 삶 팩터 (UI 드롭다운)
    life_inputs: dict   # {"succession": "예"/"아니오", "market_trend": "성장"/"보합"/"하락", "retirement_timeline": str}

    # Booking (PB·세무사 상담 예약)
    booking_result: dict

    # Family Negotiation — 이과장 협상 입력 & 결과
    daughter_inputs: dict    # {"succession_rate": float, "consulting_rate": float, "message": str}
    negotiation_result: dict # {"scenario_negotiated": {...}, "deal_summary": str, "daughter_conditions": {...}}

    # Output
    final_response: str
    final_response_raw: str  # slow_ui_adapter 적용 전 원본 (자녀 화면용)
    recommended_scenario: str  # "A" | "B" | "C" | "" — Synthesizer가 구조화 출력으로 설정
    ui_mode: str  # normal | slow
    active_agents: Annotated[list[str], operator.add]
