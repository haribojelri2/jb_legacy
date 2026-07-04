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


def _expected_figures(state: AgentState) -> list[tuple[str, int]]:
    """state의 결정론 계산 결과에서 응답에 반드시 인용돼야 할 핵심 금액 수집."""
    figures: list[tuple[str, int]] = []
    tax = state.get("tax_comparison", {})
    if tax.get("sale"):
        figures.append(("매각 세금", tax["sale"].get("total_tax", 0)))
        gw = tax["sale"].get("goodwill", 0)
        if gw:
            figures.append(("권리금", gw))
    if tax.get("special"):
        figures.append(("승계 특례 증여세", tax["special"].get("total_tax", 0)))
    port = state.get("retirement_portfolio", {})
    for key, label in (("scenario_sale", "A안 월수령"),
                       ("scenario_succession", "B안 월수령"),
                       ("scenario_hybrid", "C안 월수령")):
        sc = port.get(key)
        if sc and sc.get("monthly_income", {}).get("합계"):
            figures.append((label, sc["monthly_income"]["합계"]))
    # 0원(특례 공제)은 표기 방식이 다양하므로 대조 대상에서 제외
    return [(lbl, val) for lbl, val in figures if val]


def verify_numbers(state: AgentState, response: str) -> list[str]:
    """결정론 수치 대조(룰 엔진) — 코드 계산 금액이 응답에 인용됐는지 검증.

    synthesizer가 [계산 근거]를 코드로 조립하므로 정상 경로에서는 원 단위 금액이
    그대로 존재한다. LLM 재생성이 계산 섹션을 훼손·누락하면 여기서 걸러진다.
    반환: 누락된 '라벨(금액원)' 문자열 목록 (비면 통과).
    """
    if "[계산 근거]" not in response:
        return []  # 계산 근거 섹션이 없는 응답(단일 에이전트·일상 대화)은 대조 생략
    missing = []
    for label, value in _expected_figures(state):
        if f"{value:,}" not in response:
            missing.append(f"{label}({value:,}원)")
    return missing
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

    # ── 1차: 결정론 수치 대조 (룰 엔진, LLM 이전) ──
    missing = verify_numbers(state, response)
    if missing:
        return {
            "compliance_passed": False,
            "compliance_feedback": (
                "[계산 근거] 섹션의 수치가 원본 계산과 불일치하거나 누락되었습니다. "
                f"다음 금액을 정확히 원 단위로 다시 인용하세요: {', '.join(missing)}."
            ),
            "retry_count": retry + 1,
            "active_agents": ["ComplianceGuard"],
        }

    # ── 2차: LLM 금소법·세무 면책 문구 검수 ──
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
