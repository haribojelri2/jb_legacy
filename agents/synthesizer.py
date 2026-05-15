"""Synthesizer — 병렬 에이전트 결과를 토론 형식으로 종합."""

import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState

_SYSTEM = """\
당신은 JB Legacy 수석 어드바이저입니다.
사장님의 삶 전체에 적합한 선택 하나를 명확히 골라주세요.

출력 규칙:
- *, **, #, `, - 등 마크다운 기호를 절대 사용하지 마세요
- 번호(1. 2. 3.)와 일반 줄바꿈만 사용하세요
- 각 섹션은 아래 형식을 정확히 따르세요:

[각 전문가 의견]
(가치평가·세무·자산운용 에이전트 의견을 각 2~3줄로 요약)

[삶 적합성 분석]
다음 3가지 축으로 각 시나리오를 비교하세요.

1. 부모 안정축 (A안 강점): 세금 / 월수령액 / 20년 실질 구매력 / 원금 소진 시점
2. 가족 자산 지속축 (B안 강점): 딸 10년 누적 수익 / 10년 후 가업 재매각가치 / 가족 총자산 증가
3. 균형축 (C안 강점): 부모 현금 + 가업 일부 지속의 절충 효과

각 축에서 숫자를 반드시 인용하세요. A를 "더 많은 현금"으로만 보지 말고,
B를 "부모 손해"로만 보지 마세요. 각 선택은 다른 가치를 최적화합니다.

[최종 권고]
반드시 A(완전 매각) / B(완전 승계) / C(절충) 중 정확히 하나만 고르세요.
"A와 B 모두 고려", "상황에 따라 다름" 같은 표현은 절대 금지입니다.
추천 시나리오: X안
이유: 부모 안정(월수령·장기구매력) vs 가족 자산 지속(10년 가업가치·가족 총자산) 중 어느 쪽이 이 분의 상황에 더 중요한지를 근거로 3~4줄 이내로 설명하세요.

[주의사항]
세무사·PB와 최종 상담을 권장드립니다."""


def synthesizer_agent(state: AgentState) -> dict:
    selected = state.get("selected_agents", [])

    opinions = []
    if state.get("business_valuation", {}).get("summary"):
        opinions.append(f"[가치평가 에이전트]\n{state['business_valuation']['summary']}")
    if state.get("tax_comparison", {}).get("summary"):
        opinions.append(f"[세무·승계 에이전트]\n{state['tax_comparison']['summary']}")
    if state.get("retirement_portfolio", {}).get("advice"):
        opinions.append(f"[자산운용 에이전트]\n{state['retirement_portfolio']['advice']}")

    if not opinions:
        return {
            "final_response": "분석 결과가 없습니다. 다시 질문해 주세요.",
            "active_agents": ["Synthesizer"],
        }

    opinions_text = "\n\n".join(opinions)

    # 시나리오 숫자 직접 주입
    portfolio = state.get("retirement_portfolio", {})
    scenario_block = ""
    s_sale = portfolio.get("scenario_sale")
    s_succ = portfolio.get("scenario_succession")
    s_hybrid = portfolio.get("scenario_hybrid")
    if s_sale:
        m_sale   = s_sale["monthly_income"].get("합계", 0)
        m_succ   = s_succ["monthly_income"].get("합계", 0) if s_succ else 0
        m_hybrid = s_hybrid["monthly_income"].get("합계", 0) if s_hybrid else 0
        cap_sale = s_sale.get("total_capital", 0)
        cap_succ = s_succ.get("total_capital", 0) if s_succ else 0

        succ_line  = (
            f"B(완전 승계): 운용자산 {cap_succ:,}원 → 사장님 월 수령 {m_succ:,}원\n"
            if s_succ else ""
        )
        hybrid_line = (
            f"C(절충안): 운용자산 {s_hybrid['total_capital']:,}원 → 사장님 월 수령 {m_hybrid:,}원\n"
            if s_hybrid else ""
        )
        ab_diff = f"A vs B 차이: 월 {m_sale - m_succ:,}원\n" if s_succ else ""

        # 장기 현금흐름 테이블
        def _proj_row(label: str, proj: dict) -> str:
            if not proj:
                return ""
            ms = proj.get("milestones", {})
            rows = []
            for yr in [0, 5, 10, 20]:
                if yr in ms:
                    d = ms[yr]
                    rows.append(
                        f"  {yr:>2}년후: 명목 {d['monthly_nominal']:,}원 / "
                        f"실질(2%물가) {d['monthly_real']:,}원 / "
                        f"잔여원금 {d['remaining_capital']:,}원"
                    )
            notes = "  " + " | ".join(proj.get("notes", []))
            return f"{label}\n" + "\n".join(rows) + "\n" + notes + "\n"

        ltp_a = _proj_row("A(완전 매각) 장기 현금흐름", s_sale.get("long_term_projection"))
        ltp_b = _proj_row("B(완전 승계) 장기 현금흐름", s_succ.get("long_term_projection") if s_succ else None)
        ltp_c = _proj_row("C(절충안) 장기 현금흐름",    s_hybrid.get("long_term_projection") if s_hybrid else None)

        # 가업 지속 가치 블록
        def _continuity_row(label: str, c: dict) -> str:
            if not c:
                return ""
            return (
                f"{label} [상권 {c['market_trend']}, 연 {c['annual_growth_rate']*100:+.0f}%]\n"
                f"  딸 10년 누적 수익: {c['daughter_cumulative_income']:,}원\n"
                f"  10년 후 권리금 추정: {c['future_goodwill']:,}원 ({c['future_grade']})\n"
                f"  가족 총자산 증가: {c['family_asset_gain']:,}원\n"
            )

        cont_b = _continuity_row("B(완전 승계) 가업 지속 가치",
                                  s_succ.get("business_continuity") if s_succ else None)
        cont_c = _continuity_row("C(절충안) 가업 지속 가치",
                                  s_hybrid.get("business_continuity") if s_hybrid else None)

        scenario_block = (
            f"\n\n[시나리오 수치 — 반드시 이 숫자를 근거로 사용하세요]\n"
            f"A(완전 매각): 운용자산 {cap_sale:,}원 → 사장님 월 수령 {m_sale:,}원 (부모 안정 최대화)\n"
            f"{succ_line}"
            f"{hybrid_line}"
            f"{ab_diff}"
            f"\n[장기 재정 시뮬레이션 — 부모 관점]\n"
            f"{ltp_a}"
            f"{ltp_b}"
            f"{ltp_c}"
            f"\n[가업 지속 가치 — 가족 자산 관점]\n"
            f"{cont_b}"
            f"{cont_c}"
        )

    tax = state.get("tax_comparison", {})
    tax_block = ""
    if tax.get("sale") and tax.get("special"):
        sale_tax    = tax["sale"].get("total_tax", 0)
        special_tax = tax["special"].get("total_tax", 0)
        tax_block = (
            f"\n\n[세금 수치]\n"
            f"외부 매각 세금: {sale_tax:,}원\n"
            f"가업승계 증여세: {special_tax:,}원\n"
            f"세금 절감액: {sale_tax - special_tax:,}원"
        )

    # 삶 팩터 블록
    life = state.get("user_profile", {}).get("life_factors", {})
    life_block = ""
    if life:
        life_block = (
            f"\n\n[삶 적합성 팩터 — 사용자 직접 입력]\n"
            f"따님 승계 의향: {life.get('succession', '미입력')}\n"
            f"지역 상권 트렌드: {life.get('market_trend', '미입력')}\n"
            f"은퇴 시점: {life.get('retirement_timeline', '미입력')}"
        )

    compliance_note = state.get("compliance_feedback", "")
    retry_instruction = (
        f"\n\n[컴플라이언스 재검토 요청]\n{compliance_note}\n위 항목을 반드시 수정하세요."
        if compliance_note and not compliance_note.startswith("✅") else ""
    )

    llm = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=os.getenv("OPENAI_API_KEY"))
    synthesis = llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=(
            f"[전문 에이전트 분석 결과]\n\n{opinions_text}"
            f"{scenario_block}"
            f"{tax_block}"
            f"{life_block}\n\n"
            f"[사용자 질문]\n{state['query']}"
            f"{retry_instruction}"
        )),
    ]).content

    return {"final_response": synthesis, "active_agents": ["Synthesizer"]}
