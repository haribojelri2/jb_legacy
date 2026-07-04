"""Supervisor — LLM 기반 동적 에이전트 라우팅."""

from typing import Literal

from pydantic import BaseModel, Field
from agents.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState


class RouteDecision(BaseModel):
    """라우팅 판정 — JSON 문자열 파싱(json.loads) 의존을 제거한 구조화 출력."""
    agents: list[
        Literal["BusinessValuation", "TaxSuccession", "PostExitWM", "FamilyBridge", "Negotiation"]
    ] = Field(description="답변에 필요한 전문 에이전트 이름 목록")

_SYSTEM = """\
당신은 JB Legacy AI 오케스트레이터입니다.
사용자 질문을 분석하여 답변에 필요한 전문 에이전트 목록만 선택하세요.

에이전트 역할:
- BusinessValuation : 사업체 가치·권리금·시세 평가 (매각가, 권리금 산정)
- TaxSuccession     : 세금·증여·상속·가업승계·절세 전략 분석
- PostExitWM        : 매각 후 노후 자산운용·포트폴리오·월수령액 설계
- FamilyBridge      : 가족(자녀)에게 승계 리포트 공유
- Negotiation       : 자녀가 제안한 승계 비율·자문료 조건으로 가족 합의안(D안) 생성

선택 기준:
- 종합 상담("매각 vs 승계", "엑시트 계획", "어떻게 해야 할까") → 3개 핵심 에이전트 모두
- 세금·절세·증여 단독 질문 → TaxSuccession만
- 자산운용·포트폴리오·노후·월수령 단독 질문 → PostExitWM만
- 권리금·시세·가치평가 단독 질문 → BusinessValuation만
- 가족 공유 요청 → FamilyBridge 추가
- 자녀의 협상 조건("딸이 70% 승계를 제안", "자문료 20%면 어때") → Negotiation 추가

규칙:
1. 복합 주제면 복수 선택, 단일 주제면 해당 에이전트 하나만 선택
2. 불필요한 에이전트는 절대 포함하지 마세요"""

_CORE = ("BusinessValuation", "TaxSuccession", "PostExitWM")

# 가족 공유 게이트: 명사·동사 단독으로는 발동하지 않음 (오발동 방지)
_FAMILY_MEMBERS = ("딸", "아들", "자녀", "가족")
_SHARE_VERBS    = ("공유", "보내", "전달", "알려")

_ROUTE_MAP = {
    "BusinessValuation": "valuation",
    "TaxSuccession":     "tax",
    "PostExitWM":        "post_exit",
    "FamilyBridge":      "family",
}


def supervisor_agent(state: AgentState) -> dict:
    llm = get_llm("fast").with_structured_output(RouteDecision)
    try:
        decision: RouteDecision = llm.invoke([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=state["query"]),
        ])
        agents = list(decision.agents)
    except Exception:
        # 라우팅 호출 실패가 그래프 전체를 죽이지 않도록 격리 → 아래 폴백으로 코어 3개 투입
        agents = []

    # LLM이 핵심 에이전트를 하나도 선택 안 하면 3개 전부 기본 투입
    if not any(a in agents for a in _CORE):
        agents = list(_CORE)

    # 가족 공유 감지: (가족 명사 AND 공유 동사) 조합일 때만 FamilyBridge 추가
    # — "노후 생활비 알려줘" 같은 일반 질문에 자녀 리포트가 오발송되는 것을 방지
    q = state["query"]
    if any(m in q for m in _FAMILY_MEMBERS) and any(v in q for v in _SHARE_VERBS):
        if "FamilyBridge" not in agents:
            agents.append("FamilyBridge")

    # 협상 조건·합의안 키워드 감지 → Negotiation 자동 추가 (결정론 게이트 우선)
    if (
        state.get("daughter_inputs")
        or any(kw in q for kw in ["협상", "합의안", "D안"])
        or ("자문료" in q and ("승계" in q or "제안" in q))
    ):
        if "Negotiation" not in agents:
            agents.append("Negotiation")

    route = _ROUTE_MAP.get(agents[0], "general")

    return {
        "selected_agents": agents,
        "route":           route,
        "active_agents":   ["Supervisor"],
    }
