"""Business Valuation Agent — 사업체 가치·권리금 산정."""

import os
from agents.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState
from tools.calculators import estimate_business_value


def business_valuation_agent(state: AgentState) -> dict:
    # 미선택 시 그래프 conditional fan-out이 노드 자체를 실행하지 않음 (graph._route_dispatch)
    profile = state.get("user_profile", {})
    biz = profile.get("business", {})

    calc = estimate_business_value(
        monthly_profit=biz.get("monthly_profit", 0),
        years_operating=biz.get("years_operating", 0),
    )
    total_value = calc["goodwill_estimate"] + biz.get("deposit", 0) + biz.get("equipment_value", 0)
    calc["total_value"] = total_value
    calc["components"] = {
        "권리금 추정": calc["goodwill_estimate"],
        "보증금": biz.get("deposit", 0),
        "시설·집기": biz.get("equipment_value", 0),
        "합계": total_value,
    }

    llm = get_llm("fast")
    summary = llm.invoke([
        SystemMessage(content="사업체 가치평가 전문가입니다. 계산 결과를 자영업자 눈높이로 쉽게 설명하세요."),
        HumanMessage(content=(
            f"식당명: {biz.get('name')} | 운영기간: {biz.get('years_operating')}년\n"
            f"월 순이익: {biz.get('monthly_profit'):,}원\n"
            f"{calc['description']}\n"
            f"총 사업체 가치(권리금+보증금+시설): {total_value:,}원\n\n"
            f"질문: {state['query']}\n\n3-4문장으로 가치평가 결과를 설명해주세요."
        )),
    ]).content

    calc["summary"] = summary
    return {"business_valuation": calc, "active_agents": ["BusinessValuation"]}
