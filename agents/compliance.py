"""Compliance Guard — 금소법 + 세무 면책 검수."""

import os
from agents.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState

MAX_RETRIES = 3
_RULES = """
1. 세금 추정치는 '약', '예상', '추정' 등 불확실성을 명시해야 합니다.
2. '세무사 상담을 권장합니다' 문구가 반드시 포함되어야 합니다.
3. 투자 추천 시 '원금 손실 가능성'과 위험등급을 명시해야 합니다.
4. 최종 결정은 고객 본인 또는 담당 PB·세무사가 해야 함을 명시해야 합니다.
5. 특정 상품을 단정적으로 '최선'이라고 말해서는 안 됩니다.
"""


def compliance_agent(state: AgentState) -> dict:
    retry = state.get("retry_count", 0)
    if retry >= MAX_RETRIES:
        return {
            "compliance_passed": False,
            "compliance_feedback": "⚠️ 최대 재시도 초과. 담당 PB·세무사에게 연결합니다.",
            "active_agents": ["ComplianceGuard"],
        }

    response = state.get("final_response", "")
    if not response:
        return {"compliance_passed": True, "compliance_feedback": "✅ 검수 통과", "active_agents": ["ComplianceGuard"]}

    llm = get_llm("fast")
    result = llm.invoke([
        SystemMessage(content=f"금융·세무 소비자보호 전문가입니다.\n규칙:\n{_RULES}\n\n통과=PASS, 문제있으면=FAIL: [이유]"),
        HumanMessage(content=f"검수 대상:\n{response}"),
    ]).content.strip()

    if result.startswith("PASS"):
        return {"compliance_passed": True, "compliance_feedback": "✅ 금소법·세무 면책 검수 통과", "active_agents": ["ComplianceGuard"]}
    return {
        "compliance_passed": False,
        "compliance_feedback": result,
        "retry_count": retry + 1,
        "active_agents": ["ComplianceGuard"],
    }
