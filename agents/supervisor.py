"""Supervisor — LLM 기반 동적 에이전트 라우팅."""

import os, json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState

_SYSTEM = """\
당신은 JB Legacy AI 오케스트레이터입니다.
사용자 질문을 분석하여 답변에 필요한 전문 에이전트 목록을 결정하세요.

에이전트 역할:
- BusinessValuation : 사업체 가치·권리금·시세 평가
- TaxSuccession     : 세금·증여·상속·가업승계·절세 분석
- PostExitWM        : 매각 후 노후 자산운용·포트폴리오 설계
- FamilyBridge      : 가족(자녀)에게 승계 리포트 공유
규칙:
1. 복합 질문이면 여러 에이전트를 선택하세요.
2. 반드시 JSON 형식만 반환하세요: {"agents": ["Agent1", ...]}
3. 불필요한 에이전트는 포함하지 마세요."""


def supervisor_agent(state: AgentState) -> dict:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    resp = llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=state["query"]),
    ]).content.strip()

    try:
        data = json.loads(resp)
        agents = data.get("agents", [])
    except Exception:
        agents = []

    # 세 핵심 에이전트는 항상 함께 실행 — 서로 입력값을 공유하므로
    # 하나라도 빠지면 synthesizer가 불완전한 데이터로 다른 결론을 냄
    for core in ("BusinessValuation", "TaxSuccession", "PostExitWM"):
        if core not in agents:
            agents.append(core)

    # FamilyBridge는 공유 요청일 때만
    q = state["query"]
    if any(kw in q for kw in ["딸", "아들", "자녀", "알려", "공유", "보내", "전달"]):
        if "FamilyBridge" not in agents:
            agents.append("FamilyBridge")

    # 기존 route 필드도 유지 (UI 호환)
    route_map = {
        "BusinessValuation": "valuation",
        "TaxSuccession": "tax",
        "PostExitWM": "post_exit",
        "FamilyBridge": "family",
    }
    route = route_map.get(agents[0], "general") if agents else "general"

    return {
        "selected_agents": agents,
        "route": route,
        "active_agents": ["Supervisor"],
    }
