"""Synthesizer — 병렬 에이전트 결과를 토론 형식으로 종합."""

import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState


class SynthesisResult(BaseModel):
    recommended_scenario: str = Field(
        description="최종 추천 시나리오. A(완전 매각) / B(완전 승계) / C(절충) 중 정확히 하나. "
                    "포트폴리오 데이터가 없거나 추천 불가 시 빈 문자열."
    )
    final_response: str = Field(description="사용자에게 보여줄 전체 분석 응답 텍스트")

_SYSTEM = """\
당신은 JB Legacy 수석 어드바이저입니다.
사장님의 삶 전체에 적합한 선택 하나를 명확히 골라주세요.

출력 규칙:
- *, **, #, `, - 등 마크다운 기호를 절대 사용하지 마세요
- 번호(1. 2. 3.)와 일반 줄바꿈만 사용하세요
- 제공된 [시나리오 수치]의 원 단위 숫자를 반드시 그대로 인용하세요
- [계산 근거]와 [주의사항] 섹션은 별도로 자동 추가되므로 당신은 생성하지 마세요
- 각 시나리오(A·B·C)의 장점과 단점을 균등하게 서술하세요

생성할 섹션:

[각 전문가 의견]
(가치평가·세무·자산운용 에이전트 의견을 각 2~3줄로 요약. 세금·수익 금액을 원 단위로 포함)

[삶 적합성 분석]
다음 3가지 축으로 각 시나리오를 비교하세요. 각 축에서 강점과 약점을 모두 1~2줄씩 서술하세요.

1. 부모 안정축 (A안): 매각 세금 X원 / 월수령액 X원 / 목표 월수령액 대비 X원 부족 또는 초과 / 장점: ... / 단점: ...
   주의: "목표에 근접"처럼 애매한 표현 금지. 반드시 "목표 X원 대비 Y원 (Z원 부족/초과)"로 정확히 표현하세요.
   또한 추천 안의 단점도 구체적 수치로 명시하세요 (예: B안 추천 시 "부모 월수령 X원으로 A안 대비 Y원 낮음").
2. 가족 자산 지속축 (B안): 승계 세금 X원 / 자녀 10년 누적 수익 X원 / 장점: ... / 단점: ...
3. 균형축 (C안): 월수령액 X원 / 가족 자산 X원 / 장점: ... / 단점: ...

[최종 권고]
반드시 A(완전 매각) / B(완전 승계) / C(절충) 중 정확히 하나만 고르세요.
"A와 B 모두 고려", "상황에 따라 다름" 같은 표현은 절대 금지입니다.
추천 시나리오: X안
이유: 구체적 수치를 근거로 3~4줄 이내로 설명하세요."""


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

    # 단일 에이전트 응답: 시나리오 비교 없이 질문에 직접 답변
    _core = {"BusinessValuation", "TaxSuccession", "PostExitWM"}
    _active_core = [a for a in selected if a in _core]
    if len(_active_core) == 1:
        llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
        answer = llm.invoke([
            SystemMessage(content=(
                "당신은 JB Legacy 금융 상담사입니다.\n"
                "아래 전문가 분석을 바탕으로 사용자 질문에 직접 답변하세요.\n"
                "A/B/C 시나리오 비교는 하지 마세요. 질문에 필요한 내용만 간결하게 답하세요.\n"
                "마크다운 기호(*, **, #, `)를 사용하지 마세요.\n"
                "마지막에 세무사·PB 상담 권장 문구를 한 줄 추가하세요."
            )),
            HumanMessage(content=(
                f"[전문가 분석]\n{opinions[0]}\n\n"
                f"[사용자 질문]\n{state['query']}"
            )),
        ]).content
        return {
            "final_response": answer,
            "recommended_scenario": "",
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
                f"  자녀 10년 누적 수익: {c['daughter_cumulative_income']:,}원\n"
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
    bv  = state.get("business_valuation", {})
    tax_block = ""
    if tax.get("sale") and tax.get("special"):
        s  = tax["sale"]
        sp = tax["special"]
        sale_tax         = s.get("total_tax", 0)
        special_tax      = sp.get("total_tax", 0)
        goodwill         = s.get("goodwill", 0)
        goodwill_taxable = s.get("goodwill_taxable_portion", 0)
        biz_value        = sp.get("business_value", 0)
        sp_taxable       = sp.get("taxable", 0)
        # business_valuation에서 월순이익·배수 직접 추출 (LLM 역산 방지)
        mp       = bv.get("monthly_profit", 0)
        multiple = bv.get("multiple", 0)
        grade    = bv.get("grade", "")

        goodwill_formula = (
            f"월순이익 {mp:,}원 × {multiple}개월(영업연수 기준 {grade}) = {goodwill:,}원"
            if mp and multiple else f"권리금 {goodwill:,}원"
        )

        # 월수령 계산 근거 (각 운용상품 수익률 명시)
        monthly_basis = ""
        if s_sale and s_sale.get("total_capital"):
            cap    = s_sale["total_capital"]
            alloc  = s_sale.get("allocation", {})
            div_cap = alloc.get("월배당펀드(JB자산운용)", int(cap * 0.375))
            dep_cap = alloc.get("정기예금(전북은행)",     int(cap * 0.375))
            ann_cap = alloc.get("개인연금",               int(cap * 0.25))
            pension = s_sale.get("monthly_income", {}).get("국민연금", 0)
            monthly_basis = (
                f"\n월수령 계산(A안): 운용자산 {cap:,}원 포트폴리오\n"
                f"  월배당펀드(JB자산운용) {div_cap:,}원 × 연4.5%÷12 = {int(div_cap*0.045/12):,}원\n"
                f"  정기예금(전북은행)     {dep_cap:,}원 × 연3.55%÷12 = {int(dep_cap*0.0355/12):,}원\n"
                f"  개인연금              {ann_cap:,}원 × 연4.0%÷12 = {int(ann_cap*0.04/12):,}원\n"
                + (f"  국민연금(프로필 기준)  {pension:,}원\n" if pension else "")
            )

        tax_block = (
            f"\n\n[세금·월수령 계산 근거 — 반드시 이 단계를 [계산 근거] 섹션에 그대로 인용하세요]\n"
            f"권리금 산정: {goodwill_formula}\n"
            f"매각 세금 계산: 권리금 {goodwill:,}원 × 40%(필요경비 60% 공제)"
            f" = 과세표준 {goodwill_taxable:,}원 → 세금(지방세 10% 포함) {sale_tax:,}원\n"
            f"승계 세금 계산(조특법 제30조의6): 사업가치 {biz_value:,}원"
            f" - 10억원 공제 = 과세표준 {sp_taxable:,}원 × 10%"
            f" → 증여세(지방세 포함) {special_tax:,}원\n"
            f"세금 절감액: {sale_tax:,}원 - {special_tax:,}원 = {sale_tax - special_tax:,}원"
            f"{monthly_basis}"
        )

    # 삶 팩터 블록
    life = state.get("user_profile", {}).get("life_factors", {})
    life_block = ""
    if life:
        target = life.get("target_monthly", 0)
        target_line = f"\n목표 월수령액: {target:,}원" if target else ""
        life_block = (
            f"\n\n[삶 적합성 팩터 — 사용자 직접 입력]\n"
            f"따님 승계 의향: {life.get('succession', '미입력')}\n"
            f"지역 상권 트렌드: {life.get('market_trend', '미입력')}\n"
            f"은퇴 시점: {life.get('retirement_timeline', '미입력')}"
            f"{target_line}"
        )

    compliance_note = state.get("compliance_feedback", "")
    retry_instruction = (
        f"\n\n[컴플라이언스 재검토 요청]\n{compliance_note}\n위 항목을 반드시 수정하세요."
        if compliance_note and not compliance_note.startswith("✅") else ""
    )

    llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    structured_llm = llm.with_structured_output(SynthesisResult)
    output: SynthesisResult = structured_llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=(
            f"[전문 에이전트 분석 결과]\n\n{opinions_text}"
            f"{scenario_block}"
            f"{tax_block}"
            f"{life_block}\n\n"
            f"[사용자 질문]\n{state['query']}"
            f"{retry_instruction}"
        )),
    ])

    # [계산 근거] 섹션 — 코드에서 직접 조립 (LLM 요약 방지)
    _s_sale  = s_sale  if 's_sale'  in dir() else None
    _s_succ  = s_succ  if 's_succ'  in dir() else None
    _s_hybrid = s_hybrid if 's_hybrid' in dir() else None
    calc_section = _build_calc_section(tax, bv, _s_sale, _s_succ, _s_hybrid)

    # [주의사항] 섹션 — 금소법·투자자보호 의무 고지 (코드 고정)
    disclaimer = (
        "\n[주의사항]\n"
        "1. 세금 수치는 추정치이며 실제 세액은 개인 상황에 따라 달라질 수 있습니다.\n"
        "2. 세무사 상담을 권장드립니다.\n"
        "3. 투자 상품(펀드·연금)은 원금 손실 가능성이 있습니다.\n"
        "4. 펀드·연금 가입 전 위험등급을 반드시 확인하시기 바랍니다.\n"
        "5. 최종 결정은 고객 본인과 담당 PB·세무사가 함께 하시기 바랍니다."
    )

    # LLM 응답에 [계산 근거]를 [각 전문가 의견] 바로 다음에 삽입
    llm_text = output.final_response
    insert_marker = "[삶 적합성 분석]"
    if calc_section and insert_marker in llm_text:
        llm_text = llm_text.replace(
            insert_marker,
            calc_section + "\n" + insert_marker,
            1,
        )
    elif calc_section:
        llm_text = llm_text + "\n" + calc_section

    final_text = llm_text + "\n" + disclaimer

    return {
        "final_response": final_text,
        "recommended_scenario": output.recommended_scenario,
        "active_agents": ["Synthesizer"],
    }


def _build_calc_section(tax: dict, bv: dict, s_sale: dict | None,
                        s_succ: dict | None = None, s_hybrid: dict | None = None) -> str:
    """계산 단계를 코드에서 직접 조립 — LLM에 맡기지 않는다."""
    lines = ["[계산 근거]"]

    if tax.get("sale") and tax.get("special"):
        s  = tax["sale"]
        sp = tax["special"]
        mp       = bv.get("monthly_profit", 0)
        multiple = bv.get("multiple", 0)
        grade    = bv.get("grade", "")
        goodwill         = s.get("goodwill", 0)
        goodwill_taxable = s.get("goodwill_taxable_portion", 0)
        sale_tax         = s.get("total_tax", 0)
        biz_value        = sp.get("business_value", 0)
        sp_taxable       = sp.get("taxable", 0)
        special_tax      = sp.get("total_tax", 0)

        if mp and multiple:
            lines.append(
                f"권리금 산정: 월순이익 {mp:,}원 × {multiple}개월 배수({grade}) = {goodwill:,}원\n"
                f"  [세금 분류] 개인사업자 권리금은 기타소득(소득세법 제21조 제1항 제7호)에 해당 — 양도소득세 대상 아님"
            )
        other_income = s.get("other_income", 0)
        national_tax = s.get("national_tax", 0)
        local_tax_amount = s.get("local_tax", 0)
        total_taxable_income = goodwill_taxable + other_income
        # 누진세율 구간 역산 — Judge가 수식 직접 검증 가능하도록 공식 명시
        _brackets = [
            (300_000_000, 0.45, 65_940_000),
            (150_000_000, 0.38, 19_400_000),
            (88_000_000,  0.35, 15_440_000),
            (60_000_000,  0.24,  5_220_000),
            (40_000_000,  0.15,  1_260_000),
            (14_000_000,  0.08,    576_000),
            (0,           0.06,          0),
        ]
        _rate, _ded = 0.06, 0
        for _thr, _r, _d in _brackets:
            if total_taxable_income > _thr:
                _rate, _ded = _r, _d
                break
        lines.append(
            f"매각 세금(소득세법 제21조·시행령 제87조):\n"
            f"  권리금 {goodwill:,}원 × 40%(필요경비 60% 공제) = 기타소득 과세표준 {goodwill_taxable:,}원\n"
            + (f"  + 사업소득 {other_income:,}원 = 합산 과세표준 {total_taxable_income:,}원\n" if other_income else "")
            + f"  종합소득세({_rate*100:.0f}% 구간): {total_taxable_income:,}원 × {_rate*100:.0f}% - 누진공제 {_ded:,}원 = {national_tax:,}원\n"
            f"  지방소득세(종합소득세 × 10%): {national_tax:,}원 × 10% = {local_tax_amount:,}원\n"
            f"  최종 세금: {national_tax:,}원 + {local_tax_amount:,}원 = {sale_tax:,}원"
        )
        lines.append(
            f"승계 세금(조특법 제30조의6 가업승계 과세특례): 사업가치 {biz_value:,}원"
            f" - 10억원 공제 = 과세표준 {sp_taxable:,}원 × 10%"
            f" → 증여세(지방소득세 포함) {special_tax:,}원"
        )
        lines.append(
            "  특례 적용 요건(조특법 제30조의6):\n"
            "    - 증여자: 중소기업(연매출 120억원 이하 기준) 10년 이상 영위 대표자\n"
            "    - 수증자: 18세 이상 자녀, 증여일 前 2년 이내 가업 종사 또는 즉시 종사\n"
            "    - 사후관리: 수증 후 5년간 가업 유지 의무(위반 시 세액 추징)"
        )
        lines.append(
            f"세금 절감액: {sale_tax:,}원 - {special_tax:,}원 = {sale_tax - special_tax:,}원"
        )

    # A안 월수령 내역 — 운용자산 구성·투자금액·수익률·세후수령액 모두 명시
    if s_sale and s_sale.get("total_capital"):
        cap           = s_sale["total_capital"]
        mi            = s_sale.get("monthly_income", {})
        alloc         = s_sale.get("allocation", {})
        target_m      = s_sale.get("target_monthly", 0)
        surplus_m     = s_sale.get("surplus_monthly", 0)
        total_monthly = mi.get("합계", 0)

        # 운용자산 구성 역산: 권리금 순수령 + 기타 자산 = 총 운용자산
        if tax.get("sale"):
            net_goodwill  = goodwill - sale_tax
            other_assets  = cap - net_goodwill
            cap_breakdown = (
                f"  권리금 {goodwill:,}원 - 세금 {sale_tax:,}원 = 순수령 {net_goodwill:,}원\n"
                + (f"  + 보증금·기타 자산 {other_assets:,}원 = 총 운용자산 {cap:,}원" if other_assets > 0 else f"  = 총 운용자산 {cap:,}원")
            )
        else:
            cap_breakdown = f"  총 운용자산: {cap:,}원"

        # monthly_income 키와 allocation 키가 달라 키워드로 매핑 (상품 풀네임 포함)
        _kw_map = [("월배당", "월배당"), ("즉시연금", "즉시연금"), ("예금", "예금"), ("IRP", "IRP")]
        income_lines = []
        for prod, income in mi.items():
            if prod == "합계" or income <= 0:
                continue
            invested, full_name = 0, ""
            for inc_frag, alloc_frag in _kw_map:
                if inc_frag in prod:
                    for ak, av in alloc.items():
                        if alloc_frag in ak:
                            invested, full_name = av, ak
                            break
                    break
            if invested:
                income_lines.append(f"  {prod} [{full_name}]: 투자원금 {invested:,}원 → 월 {income:,}원")
            else:
                income_lines.append(f"  {prod}: {income:,}원")

        target_line = ""
        if target_m:
            gap_sign = "초과" if surplus_m >= 0 else "부족"
            target_line = f"\n  목표 월수령액: {target_m:,}원 / 실제: {total_monthly:,}원 ({abs(surplus_m):,}원 {gap_sign})"

        lines.append(
            f"운용자산 구성(A안 매각 후):\n{cap_breakdown}\n"
            f"월수령(A안) — 2025년 JB금융그룹 상품 기준 추정치:\n"
            + "\n".join(income_lines)
            + f"\n  합계: {total_monthly:,}원"
            + target_line
        )

    # B안/C안 월수령 내역 (부모 수령액)
    for _label, _sc in [("B안", s_succ), ("C안", s_hybrid)]:
        if not _sc or not _sc.get("total_capital"):
            continue
        _mi    = _sc.get("monthly_income", {})
        _total = _mi.get("합계", 0)
        _cap   = _sc["total_capital"]
        _tgt   = _sc.get("target_monthly", 0)
        _sur   = _sc.get("surplus_monthly", 0)
        _inc_lines = [f"  {k}: {v:,}원" for k, v in _mi.items() if k != "합계" and v > 0]
        _tgt_line  = ""
        if _tgt:
            _gap_sign = "초과" if _sur >= 0 else "부족"
            _tgt_line = f"\n  목표 월수령액: {_tgt:,}원 / 실제: {_total:,}원 ({abs(_sur):,}원 {_gap_sign})"
        lines.append(
            f"월수령({_label} 부모) — 운용자산 {_cap:,}원 기준 추정치:\n"
            + "\n".join(_inc_lines)
            + f"\n  합계: {_total:,}원" + _tgt_line
        )

    # B안/C안 자녀 누적 수익 계산 근거
    _GROWTH_HINT = {0.05: "성장 상권", 0.01: "보합 상권", -0.03: "하락 상권"}
    for label, sc in [("B안", s_succ), ("C안", s_hybrid)]:
        if not sc:
            continue
        cont = sc.get("business_continuity", {})
        if cont:
            gr    = cont.get("annual_growth_rate", 0)
            proj  = cont.get("projection_years", 10)
            cum   = cont.get("daughter_cumulative_income", 0)
            fg    = cont.get("future_goodwill", 0)
            gain  = cont.get("family_asset_gain", 0)
            mp    = bv.get("monthly_profit", 0) or (tax.get("sale", {}).get("goodwill", 0) // max(bv.get("multiple", 36), 1))
            mp_line = f"월순이익 {mp:,}원 기준 " if mp else ""
            gr_hint = _GROWTH_HINT.get(round(gr, 2), "")
            gr_label = f"{gr_hint}(사용자 입력) 연{gr*100:+.1f}%" if gr_hint else f"연{gr*100:+.1f}%"
            lines.append(
                f"자녀 누적 수익({label}): {mp_line}{gr_label}"
                f" × {proj}년 복리 적용 → 자녀 누적 수익 {cum:,}원"
                f" + {proj}년 후 권리금 {fg:,}원 = 가족 총자산 증가 {gain:,}원"
            )

    return "\n".join(lines) if len(lines) > 1 else ""
