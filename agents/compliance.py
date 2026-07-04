"""Compliance Guard — 금소법 + 세무 면책 검수."""

import os
from pydantic import BaseModel, Field
from agents.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState

MAX_RETRIES = 3


class ComplianceVerdict(BaseModel):
    """검수 판정 — 문자열 파싱(PASS/FAIL prefix) 의존을 제거한 구조화 출력."""
    passed: bool = Field(description="5개 규칙을 모두 충족하면 true")
    feedback: str = Field(
        description="불통과 시 빠진 규칙 번호와 구체적 수정 지시. 통과 시 빈 문자열"
    )
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

    llm = get_llm("smart").with_structured_output(ComplianceVerdict)
    verdict: ComplianceVerdict = llm.invoke([
        SystemMessage(content=(
            "금융·세무 소비자보호 검수 담당입니다. 아래 5개 규칙을 의미 기준으로 판단하세요.\n"
            f"{_RULES}\n"
            "판단 지침:\n"
            "- 표현이 달라도 의미가 충족되면 통과. 예: '세무사와 상담하세요'='세무사 상담 권장', "
            "'예상/추정/약'='불확실성 명시', '원금이 줄 수 있다'='원금 손실 가능성'.\n"
            "- '추천/유리하다'는 허용하며, '무조건 최선/반드시 이것'처럼 명백한 단정만 5번 위반으로 봅니다.\n"
            "확실하지 않으면 통과로 처리하세요(과도한 반려 금지)."
        )),
        HumanMessage(content=f"검수 대상:\n{response}"),
    ])

    if verdict.passed:
        return {"compliance_passed": True, "compliance_feedback": "✅ 금소법·세무 면책 검수 통과", "active_agents": ["ComplianceGuard"]}
    return {
        "compliance_passed": False,
        "compliance_feedback": verdict.feedback or "빠진 규칙을 재확인해 수정하세요 (5개 규칙 전체 점검).",
        "retry_count": retry + 1,
        "active_agents": ["ComplianceGuard"],
    }
