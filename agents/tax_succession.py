"""Tax & Succession Agent — RAG 기반 세금 시뮬레이션."""

import os
from agents.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState
from tools.calculators import calc_goodwill_tax, calc_gift_tax_special, calc_gift_tax_general, estimate_business_value
from rag.retriever import retrieve


def tax_succession_agent(state: AgentState) -> dict:
    if "TaxSuccession" not in state.get("selected_agents", []):
        return {}

    profile = state.get("user_profile", {})
    biz = profile.get("business", {})
    monthly_profit = biz.get("monthly_profit", 4_500_000)
    years_operating = biz.get("years_operating", 30)
    other_income = monthly_profit * 12  # 연간 사업소득 (매각 연도)

    # 명시적 감정가 우선, 없을 때만 수익환원법 추정 (병렬 실행으로 business_valuation 결과 불가)
    explicit_goodwill = biz.get("goodwill")
    if explicit_goodwill:
        goodwill = explicit_goodwill
        business_value = profile.get("total_business_value") or (
            goodwill + biz.get("deposit", 0) + biz.get("equipment_value", 0)
        )
    else:
        valuation = estimate_business_value(monthly_profit, years_operating)
        goodwill = valuation["goodwill_estimate"]
        business_value = goodwill + biz.get("deposit", 0) + biz.get("equipment_value", 0)

    # 1. 외부 매각 시: 권리금 기타소득세
    sale_tax = calc_goodwill_tax(goodwill=goodwill, other_income=other_income)

    # 2. 가업승계 증여세 과세특례
    special_tax = calc_gift_tax_special(business_value=business_value)

    # 3. 일반 증여세 (특례 미적용 시 비교)
    general_tax = calc_gift_tax_general(business_value=business_value)

    # RAG: 관련 세법 문서 검색
    rag_context = retrieve(state["query"] + " 가업승계 세금 권리금")

    llm = get_llm("smart")
    comparison = llm.invoke([
        SystemMessage(content=(
            "세무 전문가입니다. 아래 세법 자료와 계산 결과를 바탕으로 "
            "자영업자 눈높이에서 쉽게 설명하세요.\n"
            "규칙:\n"
            "1. 세금 금액은 반드시 원 단위로 명시하세요 (예: 28,754,000원).\n"
            "2. 가업승계 과세특례(조특법 제30조의6) 적용 시 10억원 공제 조건과 10% 세율을 설명하세요.\n"
            "3. 세금이 0원인 경우 '10억원 공제 적용으로 증여세 0원'과 같이 이유를 명시하세요.\n"
            "4. 특례 적용 조건(가업 영위 10년 이상, 중소기업 요건 등)을 간략히 언급하세요.\n"
            "5. 반드시 '세무사 상담 권장' 문구를 마지막에 추가하세요."
        )),
        HumanMessage(content=(
            f"[세법 참고 자료]\n{rag_context}\n\n"
            f"[시나리오 1 - 외부 매각]\n{sale_tax['description']}\n\n"
            f"[시나리오 2 - 가업승계 과세특례]\n{special_tax['description']}\n\n"
            f"[시나리오 3 - 일반 증여]\n{general_tax['description']}\n\n"
            f"질문: {state['query']}\n\n"
            "두 시나리오의 세금 차이, 특례 적용 조건, 어느 쪽이 유리한지 설명해주세요."
        )),
    ]).content

    return {
        "tax_comparison": {
            "sale":     sale_tax,
            "special":  special_tax,
            "general":  general_tax,
            "summary":  comparison,
        },
        "tax_rag_context": rag_context,
        "active_agents": ["TaxSuccession"],
    }
