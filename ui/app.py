"""JB Legacy — Streamlit UI"""



import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



import streamlit as st

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))



import uuid
from graph import run_query, stream_query, NODE_LABELS

from data.mock_data import USERS

from agents.booking import booking_agent

from langchain_openai import ChatOpenAI

from langchain_core.messages import HumanMessage, SystemMessage



st.set_page_config(page_title="JB Legacy", page_icon="🏮", layout="wide")



st.markdown("""

<style>

@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');

html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }



/* ── Step 1 ─────────────────────────────────────────── */

.ob-logo  { font-size: 30px; font-weight: 700; color: #111827; margin-bottom: 4px; }

.ob-sub   { font-size: 14px; color: #6b7280; margin-bottom: 32px; line-height: 1.6; }

.ob-group { font-size: 11px; font-weight: 700; letter-spacing: 1.2px;

            color: #9ca3af; text-transform: uppercase; margin: 28px 0 10px 0; }



/* ── Step 2 header ──────────────────────────────────── */

.s2-header { padding-bottom: 12px; border-bottom: 1px solid #e5e7eb; margin-bottom: 20px; }

.s2-title  { font-size: 16px; font-weight: 700; color: #111827; }

.s2-meta   { font-size: 12px; color: #9ca3af; margin-left: 12px; }



/* ── Panel ──────────────────────────────────────────── */

.panel-label { font-size: 11px; font-weight: 700; letter-spacing: 1.2px;

               color: #9ca3af; text-transform: uppercase; margin: 0 0 14px 0; }

.analysis-divider { border-left: 1px solid #e5e7eb; padding-left: 24px; }



/* ── 분석 결과 패널 (Claude artifact 스타일) ───────────── */





/* ── Reused analysis styles ─────────────────────────── */

.section-label { font-size: 11px; font-weight: 700; letter-spacing: 1.2px;

                 color: #888; text-transform: uppercase; margin: 20px 0 8px 0; }

.response-box  { font-size: 14px; line-height: 1.9; color: #1a1a2e;

                 background: #f8f6ff; border-left: 4px solid #5b21b6;

                 padding: 16px 20px; border-radius: 0 8px 8px 0; white-space: pre-wrap; }

.response-slow { font-size: 20px; line-height: 2.2; color: #2d1b00;

                 background: #fffbf0; border-left: 6px solid #c8963e;

                 padding: 22px 26px; border-radius: 0 10px 10px 0; white-space: pre-wrap; }

.rationale-box { background: #f0fdf4; border: 1px solid #86efac;

                 padding: 14px 18px; border-radius: 8px; font-size: 13px;

                 color: #14532d; line-height: 1.8; white-space: pre-wrap; }

.child-box     { font-size: 15px; line-height: 1.8; background: #f0fdf4; color: #14532d;

                 border-left: 5px solid #16a34a; padding: 18px 22px;

                 border-radius: 0 10px 10px 0; white-space: pre-wrap; }

.tax-card      { background: white; border: 1px solid #e5e7eb; padding: 16px;

                 border-radius: 10px; margin: 4px 0; box-shadow: 0 1px 3px rgba(0,0,0,.05); }

.booking-box   { background: #eff6ff; border: 1px solid #93c5fd;

                 padding: 14px 18px; border-radius: 8px; font-size: 13px; color: #1e3a5f; }

.compliance-ok  { font-size: 12px; color: #16a34a; }

.compliance-err { font-size: 12px; color: #dc2626; }

.agent-card    { background: #0f0f23; color: #e0e0e0; padding: 12px 14px;

                 border-radius: 8px; font-size: 12px; line-height: 2.0; }

.agent-on  { color: #4ade80; }

.agent-off { color: #555; }

</style>

""", unsafe_allow_html=True)



ALL_AGENTS = ["Supervisor", "Profiler", "BusinessValuation",

              "TaxSuccession", "PostExitWM", "Synthesizer", "FamilyBridge", "ComplianceGuard", "Booking"]



_TARGET_OPTS = {

    "150만원": 1_500_000, "200만원": 2_000_000, "250만원": 2_500_000,

    "300만원": 3_000_000, "350만원": 3_500_000, "400만원": 4_000_000,

}





# ── Helper functions ──────────────────────────────────────────────────────────



def _is_analysis_request(query: str) -> bool:

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

    resp = llm.invoke([HumanMessage(content=(

        "다음 메시지가 사업 매각·승계·세금·노후 설계 등 재무 분석을 요청하는 것인지 판단하세요.\n"

        "분석 요청 예시: 세금 얼마야, 승계하면 어때, 팔면 얼마 남아, 노후 준비, 권리금, 포트폴리오 등\n"

        "일반 대화 예시: 인사, 감사, 안녕, 네, 아니오, 짧은 감탄사 등\n"

        f"메시지: {query}\n"

        "ANALYSIS 또는 CHAT 중 하나만 반환하세요."

    ))]).content.strip()

    return resp == "ANALYSIS"





def _is_followup(query: str) -> bool:

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

    resp = llm.invoke([HumanMessage(content=(

        "다음 질문이 이미 완료된 사업 엑시트 분석에 대한 후속 질문인지 판단하세요.\n"

        "후속 질문 예시: 결과 설명, 수치 재질문, 이유 설명, 포트폴리오/세금/시나리오 해석 요청, 왜/더/자세히/어떻게/비교 키워드\n"

        "새 분析 예시: 아무 분析도 없는 첫 질문, 완전히 다른 주제로 처음부터 새로 계산하는 요청\n"



        f"질문: {query}\n"

        "FOLLOWUP 또는 NEW_ANALYSIS 중 하나만 반환하세요."

    ))]).content.strip()

    return resp == "FOLLOWUP"





def _followup_response(query: str, last_result: dict, history: list) -> str:

    final = last_result.get("final_response_raw") or last_result.get("final_response", "")

    portfolio = last_result.get("retirement_portfolio", {})

    tax = last_result.get("tax_comparison", {})



    context_parts = []

    if final:

        context_parts.append(f"[이전 분석 결과]\n{final}")



    s_sale   = portfolio.get("scenario_sale", {})

    s_succ   = portfolio.get("scenario_succession")

    s_hybrid = portfolio.get("scenario_hybrid")

    if s_sale:

        m_a = s_sale.get("monthly_income", {}).get("합계", 0)

        m_b = s_succ["monthly_income"].get("합계", 0) if s_succ else 0

        m_c = s_hybrid["monthly_income"].get("합계", 0) if s_hybrid else 0

        nums = (

            f"A안 월수령: {m_a:,}원 / 운용자산: {s_sale.get('total_capital',0):,}원\n"

            + (f"B안 월수령: {m_b:,}원 / 운용자산: {s_succ.get('total_capital',0):,}원\n" if s_succ else "")

            + (f"C안 월수령: {m_c:,}원 / 운용자산: {s_hybrid.get('total_capital',0):,}원\n" if s_hybrid else "")

        )

        context_parts.append(f"[시나리오 수치]\n{nums}")



    if tax.get("sale"):

        context_parts.append(

            f"[세금 수치]\n"

            f"매각 세금: {tax['sale'].get('total_tax',0):,}원\n"

            f"승계 증여세: {tax.get('special',{}).get('total_tax',0):,}원"

        )



    if history:

        turns = "\n".join(

            f"{'사용자' if m['role']=='user' else '어드바이저'}: {m['content']}"

            for m in history[-6:]

        )

        context_parts.append(f"[이전 대화]\n{turns}")



    context = "\n\n".join(context_parts)

    llm = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=os.getenv("OPENAI_API_KEY"))

    return llm.invoke([

        SystemMessage(content=(

            "JB Legacy AI 어드바이저입니다. 이전 분석 결과를 참고하여 후속 질문에 답하세요.\n"

            "마크다운 기호(*, **, #, `)를 사용하지 마세요. 숫자는 정확히 인용하세요.\n"

            "세금 수치는 반드시 '추정치'임을 명시하고 '세무사 상담을 권장합니다' 문구를 포함하세요.\n"

            "투자 관련 내용은 '원금 손실 가능성이 있습니다'를 명시하세요.\n"

            "최종 결정은 고객 본인 또는 담당 PB·세무사가 해야 함을 포함하세요.\n"

            "답변은 5~7줄 이내로."

        )),

        HumanMessage(content=f"{context}\n\n사용자 질문: {query}"),

    ]).content





_COMPLIANCE_RULES = """

1. 세금 추정치는 '약', '예상', '추정' 등 불확실성을 명시해야 합니다.

2. '세무사 상담을 권장합니다' 문구가 반드시 포함되어야 합니다.

3. 투자 추천 시 '원금 손실 가능성'과 위험등급을 명시해야 합니다.

4. 최종 결정은 고객 본인 또는 담당 PB·세무사가 해야 함을 명시해야 합니다.

5. 특정 상품을 단정적으로 '최선'이라고 말해서는 안 됩니다.

"""





def _run_compliance(text: str) -> tuple[bool, str]:

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

    result = llm.invoke([

        SystemMessage(content=f"금융·세무 소비자보호 전문가입니다.\n규칙:\n{_COMPLIANCE_RULES}\n\n통과=PASS, 문제있으면=FAIL: [이유]"),

        HumanMessage(content=f"검수 대상:\n{text}"),

    ]).content.strip()

    if result.startswith("PASS"):

        return True, "✅ 금소법·세무 면책 검수 통과"

    return False, result





def _strip_md(text: str) -> str:

    text = re.sub(r'\*{1,3}', '', text)

    text = re.sub(r'#{1,6}\s?', '', text)

    text = re.sub(r'`{1,3}', '', text)

    text = re.sub(r'_{1,2}', '', text)

    return text.strip()





def _parse_sections(text: str) -> dict:

    sections = {}

    pattern = r'\[([^\]]+)\]\s*(.*?)(?=\[|$)'

    for m in re.finditer(pattern, text, re.DOTALL):

        key = m.group(1).strip()

        val = _strip_md(m.group(2).strip())

        sections[key] = val

    if not sections:

        sections["종합 의견"] = _strip_md(text)

    return sections





def _agent_panel(active: list):

    lines = []

    for a in ALL_AGENTS:

        if a in active:

            lines.append(f'<span class="agent-on">● {a}</span>')

        else:

            lines.append(f'<span class="agent-off">○ {a}</span>')

    st.markdown(

        '<div class="agent-card">' + "<br>".join(lines) + "</div>",

        unsafe_allow_html=True,

    )





def _tax_cards(tax: dict):

    if not tax:

        return

    sale    = tax.get("sale", {})

    special = tax.get("special", {})

    saving  = sale.get("total_tax", 0) - special.get("total_tax", 0)

    c1, c2 = st.columns(2)

    with c1:

        st.markdown('<div class="tax-card">', unsafe_allow_html=True)

        st.markdown("##### 외부 매각 시")

        st.metric("예상 세금", f"{sale.get('total_tax', 0):,}원")

        st.caption("권리금 기타소득세 (필요경비 60% 공제)")

        st.markdown('</div>', unsafe_allow_html=True)

    with c2:

        st.markdown('<div class="tax-card">', unsafe_allow_html=True)

        st.markdown("##### 가업승계 과세특례")

        st.metric("예상 세금", f"{special.get('total_tax', 0):,}원",

                  delta=f"-{saving:,}원 절세" if saving > 0 else None,

                  delta_color="inverse")

        st.caption("조세특례제한법 제30조의6")

        st.markdown('</div>', unsafe_allow_html=True)





def _portfolio_section(portfolio: dict, recommended: str = ""):

    if not portfolio:

        return



    s_sale   = portfolio.get("scenario_sale")

    s_succ   = portfolio.get("scenario_succession")

    s_hybrid = portfolio.get("scenario_hybrid")



    if not s_sale:

        return



    rec = recommended.upper()

    def _is_rec(key):

        return key in rec



    scenarios = [("A. 완전 매각", s_sale, _is_rec("A"))]

    if s_succ:

        scenarios.append(("B. 완전 승계", s_succ, _is_rec("B")))

    if s_hybrid:

        scenarios.append(("C. 절충안", s_hybrid, _is_rec("C")))



    st.markdown('<p class="section-label">노후 현금흐름 — 시나리오별 포트폴리오</p>', unsafe_allow_html=True)

    cols = st.columns(len(scenarios))



    def _scenario_col(col, label, scenario, highlight=False):

        with col:

            header = f"**{label}** {'✓ 추천' if highlight else ''}"

            st.markdown(header)

            m = scenario["monthly_income"]

            surplus = scenario["surplus_monthly"]

            st.metric("월 수령 합계", f"{m.get('합계',0):,}원",

                      delta=f"목표 대비 {surplus:+,}원",

                      delta_color="normal" if surplus >= 0 else "inverse")

            st.caption(f"운용자산: {scenario['total_capital']:,}원")

            st.divider()



            total = scenario["total_capital"] or 1

            for k, v in scenario.get("allocation", {}).items():

                pct = v / total

                st.progress(pct, text=f"{k}\n{v:,}원 ({pct*100:.0f}%)")



            st.markdown("**월 수령 내역**")

            for k, v in m.items():

                if k != "합계":

                    st.caption(f"{k}: {v:,}원")



            proj = scenario.get("long_term_projection", {})

            milestones = proj.get("milestones", {})

            if milestones:

                with st.expander("장기 재정 전망 (10년·20년)"):

                    rows = []

                    for yr in [0, 5, 10, 20]:

                        d = milestones.get(yr)

                        if d:

                            rows.append({

                                "시점": f"{yr}년 후",

                                "명목 월수령": f"{d['monthly_nominal']:,}원",

                                "실질(물가2%)": f"{d['monthly_real']:,}원",

                                "잔여원금": f"{d['remaining_capital']:,}원",

                            })

                    import pandas as pd

                    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

                    for note in proj.get("notes", []):

                        st.caption(f"• {note}")



            cont = scenario.get("business_continuity")

            if cont:

                with st.expander("가업 지속 가치 (자녀·가족 관점)"):

                    st.caption(f"상권 트렌드: {cont['market_trend']} (연 {cont['annual_growth_rate']*100:+.0f}%)")

                    st.metric("딸 10년 누적 수익", f"{cont['daughter_cumulative_income']:,}원")

                    st.metric("10년 후 권리금 추정", f"{cont['future_goodwill']:,}원",

                              delta=f"{cont['future_grade']}")

                    st.metric("가족 총자산 증가", f"{cont['family_asset_gain']:,}원")

                    m10 = cont["future_monthly_profit"]

                    st.caption(f"10년 후 월순이익 추정: {m10:,}원 ({cont['future_multiple']}개월 배수 적용)")



            rationale = scenario.get("portfolio_rationale", "")

            if rationale:

                with st.expander("구성 이유"):

                    st.text(rationale)



    for col, (label, scenario, highlight) in zip(cols, scenarios):

        _scenario_col(col, label, scenario, highlight)



    st.caption("⚠️ 펀드·연금 상품은 원금 손실 가능성이 있습니다. B안은 순수익 20%, C안은 순수익 10%를 딸에게서 10년간 자문료로 수취하는 현실적 타협안을 가정했습니다.")





def _rationale_box(sections: dict, tax: dict, portfolio: dict):

    parts = []

    if sections.get("핵심 선택지와 근거"):

        parts.append(sections["핵심 선택지와 근거"])

    elif tax:

        sale_tax    = tax.get("sale", {}).get("total_tax", 0)

        special_tax = tax.get("special", {}).get("total_tax", 0)

        if sale_tax and special_tax:

            saving = sale_tax - special_tax

            parts.append(

                f"외부 매각 세금 {sale_tax:,}원 vs 가업승계 특례 {special_tax:,}원\n"

                f"가업승계 선택 시 {saving:,}원 절세 효과"

            )

    if portfolio:

        surplus = portfolio.get("surplus_monthly", 0)

        total_m = portfolio.get("monthly_income", {}).get("합계", 0)

        if total_m:

            parts.append(

                f"운용 자산 기반 월 수령 합계 {total_m:,}원\n"

                f"목표 생활비 300만원 대비 월 {surplus:+,}원"

            )

    if not parts:

        return

    st.markdown('<p class="section-label">추천 근거</p>', unsafe_allow_html=True)

    st.markdown(

        '<div class="rationale-box">' + "\n\n".join(parts) + "</div>",

        unsafe_allow_html=True,

    )





def _response_section(final: str, is_slow: bool, sections: dict):

    st.markdown('<p class="section-label">종합 의견</p>', unsafe_allow_html=True)

    box_cls = "response-slow" if is_slow else "response-box"

    display = sections.get("최종 권고") or sections.get("종합 의견") or _strip_md(final)

    st.markdown(f'<div class="{box_cls}">{display}</div>', unsafe_allow_html=True)



    if sections.get("각 전문가 의견"):

        with st.expander("전문가별 세부 의견 보기"):

            st.text(sections["각 전문가 의견"])



    if sections.get("주의사항"):

        st.caption(f"⚠️ {sections['주의사항']}")





def _booking_section(booking: dict):

    if not booking or not booking.get("confirmed"):

        return

    st.markdown('<p class="section-label">PB 상담 예약</p>', unsafe_allow_html=True)

    msg    = booking.get("confirm_message", "")

    detail = (

        f"{booking.get('branch', '')}  |  "

        f"{booking.get('date', '')} {booking.get('time', '')}  |  "

        f"Tel {booking.get('tel', '')}"

    )

    docs = "  준비서류: " + ", ".join(booking.get("prep_docs", []))

    st.markdown(

        f'<div class="booking-box">{_strip_md(msg)}<br><br>{detail}<br>{docs}</div>',

        unsafe_allow_html=True,

    )





def _child_dashboard(result: dict | None):

    parent = USERS.get("lee_sajang", {})

    biz    = parent.get("business", {})

    st.markdown("#### 아버지(이사장) 은퇴 플랜 리포트")

    c1, c2, c3 = st.columns(3)

    c1.metric("운영 기간", f"{biz.get('years_operating')}년")

    c2.metric("월 순이익", f"{biz.get('monthly_profit', 0):,}원")

    c3.metric("사업체 추정가치", f"{parent.get('total_business_value', 0):,}원")

    if result:

        st.divider()

        _tax_cards(result.get("tax_comparison", {}))

        _portfolio_section(result.get("retirement_portfolio", {}))

        final = result.get("final_response_raw") or result.get("final_response", "")

        if final:

            sections = _parse_sections(final)

            st.markdown('<p class="section-label">종합 요약</p>', unsafe_allow_html=True)

            summary = sections.get("최종 권고") or sections.get("종합 의견") or _strip_md(final)

            st.markdown(f'<div class="child-box">{summary}</div>', unsafe_allow_html=True)

    else:

        st.info("Scene 1 또는 Scene 3을 먼저 실행해주세요.")





# ── Step management ───────────────────────────────────────────────────────────

if "step" not in st.session_state:

    st.session_state["step"] = 1

if "thread_id" not in st.session_state:

    st.session_state["thread_id"] = str(uuid.uuid4())





# ════════════════════════════════════════════════════════════════════════════

# STEP 1 — 기본 정보 입력

# ════════════════════════════════════════════════════════════════════════════

if st.session_state["step"] == 1:

    _, col, _ = st.columns([1, 1.6, 1])

    with col:

        st.markdown("")

        st.markdown("")

        st.markdown('<p class="ob-logo">🏮 JB Legacy</p>', unsafe_allow_html=True)

        st.markdown(

            '<p class="ob-sub">평생 일군 가게, 가장 명예롭게 마무리하는<br>AI 가업승계·엑시트 에이전트</p>',

            unsafe_allow_html=True,

        )



        st.markdown('<p class="ob-group">페르소나</p>', unsafe_allow_html=True)

        selected_user = st.radio(

            "역할",

            ["lee_sajang", "lee_gwajang"],

            format_func=lambda x: {

                "lee_sajang":  "👴 이사장  62세 · 전주 · 30년 한정식",

                "lee_gwajang": "👩 이과장  32세 · 서울 · 직장인 딸",

            }[x],

            label_visibility="collapsed",

        )



        # 이과장은 입력 폼 불필요 — 딸 대시보드로 바로 이동

        if selected_user == "lee_gwajang":

            st.info("이과장 화면은 아버지의 분석 결과를 공유 받아 열람합니다.\n이사장이 먼저 분석을 완료해야 합니다.")

            st.markdown("")

            if st.button("이과장 화면 열기 →", type="primary", use_container_width=True):

                st.session_state.update({

                    "selected_user": "lee_gwajang",

                    "life_inputs": {},

                    "step": 2,

                })

                st.rerun()

        else:

            st.markdown('<p class="ob-group">상황 입력</p>', unsafe_allow_html=True)

            r1c1, r1c2, r1c3 = st.columns(3)

            with r1c1:

                succession_input = st.selectbox("따님 승계 의향", ["예", "아니오"])

            with r1c2:

                market_input     = st.selectbox("지역 상권 트렌드", ["성장", "보합", "하락"], index=2)

            with r1c3:

                retirement_input = st.selectbox("은퇴 시점", ["1년 이내", "3년 이내", "5년 이상"])

            r2c1, r2c2, _ = st.columns(3)

            with r2c1:

                target_label       = st.selectbox("월 목표 생활비", list(_TARGET_OPTS.keys()), index=3)

            with r2c2:

                home_pension_input = st.selectbox("주택연금 활용", ["아니오", "예"])



            st.markdown("")

            if st.button("분석 시작하기 →", type="primary", use_container_width=True):

                st.session_state.update({

                    "selected_user":  selected_user,

                    "life_inputs":    {

                        "succession":          succession_input,

                        "market_trend":        market_input,

                        "retirement_timeline": retirement_input,

                        "target_monthly":      _TARGET_OPTS[target_label],

                        "home_pension":        home_pension_input,

                    },

                    "chat_history":   [],

                    "last_result":    None,

                    "step": 2,

                })

                st.rerun()





# ════════════════════════════════════════════════════════════════════════════

# STEP 2 — 대화 + 분석 결과

# ════════════════════════════════════════════════════════════════════════════

else:

    selected_user = st.session_state.get("selected_user", "lee_sajang")

    profile       = USERS.get(selected_user, {})

    is_slow       = profile.get("slow_ui", False)

    life          = st.session_state.get("life_inputs", {})



    # ── 헤더 ─────────────────────────────────────────────────────────────

    hc1, hc2 = st.columns([1, 9])

    with hc1:

        if st.button("← 처음으로"):

            # 처음으로 돌아갈 때 대화 기록 초기화

            st.session_state.update({"step": 1, "chat_history": [], "followup_compliance_fb": ""})

            st.rerun()

    with hc2:

        meta = (

            f"{profile.get('name', '')}  ·  "

            f"승계 {life.get('succession','—')}  ·  "

            f"상권 {life.get('market_trend','—')}  ·  "

            f"목표 {life.get('target_monthly',0)//10000}만원/월  ·  "

            f"주택연금 {life.get('home_pension','—')}"

        ) if selected_user == "lee_sajang" else profile.get("name", "")

        st.markdown(

            f'<div class="s2-header">'

            f'<span class="s2-title">🏮 JB Legacy</span>'

            f'<span class="s2-meta">{meta}</span>'

            f'</div>',

            unsafe_allow_html=True,

        )



    # ── 이과장 전용 화면 ──────────────────────────────────────────────────

    if selected_user == "lee_gwajang":

        parent_result = st.session_state.get("split_result") or st.session_state.get("last_result")

        _child_dashboard(parent_result)

        st.divider()

        st.caption("세금 계산은 추정치입니다. 정확한 세액은 반드시 세무사 상담을 받으시기 바랍니다.")

        st.stop()



    # ── 이사장: 분석 결과 유무에 따라 1컬럼 or 2컬럼 ─────────────────────

    _result_preview = (

        st.session_state.get("last_result")

        if st.session_state.get("last_user") == selected_user

        else None

    )

    _has_result = bool(_result_preview and (

        _result_preview.get("tax_comparison")

        or _result_preview.get("retirement_portfolio")

        or _result_preview.get("child_view_active")

    ))



    if _has_result or st.session_state.get("child_view_active"):

        col_chat, col_analysis = st.columns([1.1, 1], gap="large")

    else:

        col_chat = st.container()

        col_analysis = None



    with col_chat:

        st.markdown('<p class="panel-label">대화</p>', unsafe_allow_html=True)

        chat_history = st.session_state.get("chat_history", [])



        if not chat_history:

            st.markdown(

                '<div style="margin-top:80px;text-align:center;color:#9ca3af;">'

                '<div style="font-size:32px;margin-bottom:12px">🏮</div>'

                '<div style="font-size:15px;font-weight:600;color:#374151;margin-bottom:8px">무엇이 궁금하신가요?</div>'

                '<div style="font-size:13px;line-height:1.8">'

                '매각 vs 승계 세금 비교 · 노후 현금흐름 시뮬레이션<br>'

                '권리금 계산 · PB 상담 예약'

                '</div></div>',

                unsafe_allow_html=True,

            )

        else:

            for msg in chat_history:

                with st.chat_message(msg["role"]):

                    st.write(msg["content"])



            followup_cfb = st.session_state.get("followup_compliance_fb", "")

            if followup_cfb:

                cls = "compliance-ok" if followup_cfb.startswith("✅") else "compliance-err"

                st.markdown(f'<p class="{cls}">{followup_cfb}</p>', unsafe_allow_html=True)



    if col_analysis is not None:

     with col_analysis:

        st.markdown('<div class="analysis-divider">', unsafe_allow_html=True)

        st.markdown('<p class="panel-label">분석 결과</p>', unsafe_allow_html=True)

        _analysis_container = st.container(height=720, border=False)



        result = (

            st.session_state.get("last_result")

            if st.session_state.get("last_user") == selected_user

            else None

        )



        with _analysis_container:

         child_active = st.session_state.get("child_view_active", False)



         if child_active and result:

             if st.button("← 아버지 화면으로", key="back_parent"):

                 st.session_state["child_view_active"] = False

                 st.rerun()

             st.divider()

             _child_dashboard(result)

         elif result:

             if result.get("clarification_needed"):

                 st.warning(f"추가 정보 필요\n\n{result['clarification_needed']}")

                 clarify_ans = st.text_input("답변 입력", key="clarify_input")

                 if st.button("답변 후 분석", key="clarify_run"):

                     with st.status("분석 중...", expanded=True) as _status:

                         _final = {}

                         for _node, _upd in stream_query(

                             selected_user,

                             st.session_state.get("last_query", ""),

                             clarification_answer=clarify_ans,

                             life_inputs=life,

                             thread_id=st.session_state["thread_id"],

                         ):

                             if _node == "__done__":

                                 _final = _upd

                             else:

                                 _status.update(label=f"⏳ {NODE_LABELS.get(_node, _node)}...")

                         _status.update(label="✅ 분석 완료", state="complete")

                     st.session_state["last_result"] = _final

                     st.rerun()

             else:

                 with st.expander("에이전트 현황", expanded=False):

                     _agent_panel(result.get("active_agents", []))

                     agents = result.get("selected_agents", [])

                     if agents:

                         st.caption("투입: " + " · ".join(agents))



                     life_f = result.get("user_profile", {}).get("life_factors", {})

                     if life_f:

                         _FACTOR_LABEL = {

                             "succession":          "따님 승계 의향",

                             "market_trend":        "상권 트렌드",

                             "retirement_timeline": "은퇴 시점",

                             "target_monthly":      "월 목표 생활비",

                             "home_pension":        "주택연금 활용",

                         }

                         _COLOR = {

                             "예": "#16a34a", "아니오": "#f59e0b",

                             "성장": "#16a34a", "보합": "#f59e0b", "하락": "#dc2626",

                             "1년 이내": "#dc2626", "3년 이내": "#f59e0b", "5년 이상": "#16a34a",

                         }

                         for key, label in _FACTOR_LABEL.items():

                             val = life_f.get(key)

                             if val is None:

                                 continue

                             if key == "target_monthly":

                                 display, color = f"{val:,}원", "#5b21b6"

                             else:

                                 display = str(val)

                                 color   = _COLOR.get(display, "#888")

                             st.markdown(

                                 f'<div style="font-size:12px;margin:3px 0">'

                                 f'{label}: <span style="color:{color};font-weight:600">{display}</span></div>',

                                 unsafe_allow_html=True,

                             )



                 _tax_cards(result.get("tax_comparison", {}))

                 final_resp = result.get("final_response", "")

                 rec_match = __import__('re').search(r'추천\s*시나리오[^\w]*([ABC])', final_resp)

                 recommended = rec_match.group(1) if rec_match else ""

                 _portfolio_section(result.get("retirement_portfolio", {}), recommended)

                 _booking_section(result.get("booking_result", {}))



                 with st.expander("상세 분석 데이터"):

                     bv = result.get("business_valuation", {})

                     if bv.get("components"):

                         st.markdown("사업체 가치 구성")

                         for k, v in bv["components"].items():

                             st.write(f"{k}: {v:,}원")

                     rag = result.get("tax_rag_context", "")

                     if rag:

                         st.markdown("참조 세법·상품 문서 (RAG)")

                         st.text(rag[:1000] + "...")



                 cfb = result.get("compliance_feedback", "")

                 if cfb:

                     cls = "compliance-ok" if cfb.startswith("✅") else "compliance-err"

                     st.markdown(f'<p class="{cls}">{cfb}</p>', unsafe_allow_html=True)



                 st.divider()

                 if st.button("👩 딸(이과장)에게 공유하기", use_container_width=True, key="share_child"):

                     st.session_state["split_result"]      = result

                     st.session_state["child_view_active"] = True

                     st.rerun()

         else:

             st.caption("질문을 입력하면 분석 결과가 여기에 표시됩니다.")



        st.markdown('</div>', unsafe_allow_html=True)



    # ── 채팅 입력 (페이지 하단 고정) ─────────────────────────────────────

    _FAMILY_KW  = ["딸", "아들", "자녀", "알려", "공유", "보내", "전달"]

    _BOOKING_KW = ["예약", "상담 받", "만나고", "방문", "세무사 연결", "PB 연결", "예약해", "상담해", "연결해"]



    pending   = st.session_state.pop("pending_query", None)

    typed_q   = st.chat_input("궁금한 것을 물어보세요..." if not is_slow else "말씀해 주세요...")

    effective_q = typed_q or pending



    if effective_q:

        cached       = st.session_state.get("last_result")

        has_analysis = bool(cached and (cached.get("tax_comparison") or cached.get("retirement_portfolio")))

        is_family_q  = any(kw in effective_q for kw in _FAMILY_KW)

        current_life = st.session_state.get("life_inputs", {})

        cache_valid  = (

            st.session_state.get("last_user") == selected_user

            and st.session_state.get("last_life_inputs") == current_life

        )



        is_booking_q = any(kw in effective_q for kw in _BOOKING_KW)

        chat_history = st.session_state.get("chat_history", [])

        chat_history.append({"role": "user", "content": effective_q})



        if is_booking_q:

            with st.spinner("예약 처리 중..."):

                profile = USERS.get(selected_user, {})

                booking_state = {

                    "query": effective_q,

                    "selected_agents": ["Booking"],

                    "user_profile": profile,

                    "compliance_feedback": "",

                    "retry_count": 0,

                }

                booking_out = booking_agent(booking_state)

            booking_info = booking_out.get("booking_result", {})

            reply = booking_info.get("confirm_message", "예약이 완료되었습니다.")

            chat_history.append({"role": "assistant", "content": reply})

            # 기존 분석 결과에 예약 정보 병합

            if cached:

                cached["booking_result"] = booking_info

                st.session_state["last_result"] = cached

            st.session_state["chat_history"] = chat_history

            st.rerun()



        elif is_family_q and has_analysis:

            st.session_state["split_result"]      = cached

            st.session_state["child_view_active"] = True

            reply = "이전 분석 결과를 딸(이과장)에게 공유했습니다. 오른쪽 패널에서 확인하세요."

            chat_history.append({"role": "assistant", "content": reply})

            st.session_state["chat_history"] = chat_history

            st.rerun()



        elif has_analysis and cache_valid and _is_followup(effective_q):

            with st.spinner("답변 중..."):

                followup_ans  = ""

                compliance_fb = ""

                for _attempt in range(3):

                    followup_ans = _followup_response(

                        effective_q, cached, chat_history[:-1]

                    )

                    passed, compliance_fb = _run_compliance(followup_ans)

                    if passed:

                        break

                else:

                    compliance_fb = "⚠️ 컴플라이언스 재시도 초과. 담당 PB·세무사에게 문의하세요."

            chat_history.append({"role": "assistant", "content": followup_ans})

            st.session_state["chat_history"]           = chat_history

            st.session_state["followup_compliance_fb"] = compliance_fb

            st.rerun()



        elif not _is_analysis_request(effective_q):

            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=os.getenv("OPENAI_API_KEY"))

            reply = llm.invoke([

                SystemMessage(content="JB Legacy AI 어드바이저입니다. 간단히 대화에 응답하세요. 재무 분석이 필요하면 관련 질문을 해달라고 안내하세요."),

                HumanMessage(content=effective_q),

            ]).content

            chat_history.append({"role": "assistant", "content": reply})

            st.session_state["chat_history"] = chat_history

            st.rerun()



        else:

            with st.status("분석 시작...", expanded=True) as _status:

                result = {}

                for _node, _upd in stream_query(

                    selected_user, effective_q,

                    life_inputs=current_life,

                    thread_id=st.session_state["thread_id"],

                ):

                    if _node == "__done__":

                        result = _upd

                    else:

                        _status.update(label=f"⏳ {NODE_LABELS.get(_node, _node)}...")

                _status.update(label="✅ 분석 완료", state="complete")



            final    = result.get("final_response_raw") or result.get("final_response", "")

            sections = _parse_sections(final) if final else {}

            summary  = (

                sections.get("최종 권고")

                or sections.get("종합 의견")

                or _strip_md(final)[:300]

                or "분석이 완료되었습니다. 오른쪽 패널에서 상세 결과를 확인하세요."

            )

            chat_history.append({"role": "assistant", "content": summary})



            st.session_state.update({

                "last_result":             result,

                "last_user":               selected_user,

                "last_query":              effective_q,

                "last_life_inputs":        current_life,

                "chat_history":            chat_history,

                "followup_compliance_fb":  "",

                "child_view_active":       False,

            })

            st.rerun()





