"""JB Legacy — Streamlit UI"""



import sys, os, re

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Streamlit 재실행 시 깨진 모듈 캐시 제거
for _k in [k for k in sys.modules if k in ("graph",) or k.startswith("agents.") or k.startswith("tools.") or k.startswith("data.")]:
    del sys.modules[_k]

import streamlit as st

from dotenv import load_dotenv

load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

import uuid
from graph import run_query, stream_query, NODE_LABELS

from data.mock_data import USERS

from agents.booking import booking_agent

from agents.negotiation import negotiation_agent

from agents.param_adjuster import detect_param_changes

from agents.early_warning import calc_health_score
from agents.dynamic_valuation import calc_dynamic_goodwill
from agents.youth_matching import get_youth_matching_info
from agents.contract_manager import build_contract_plan
from agents.fraud_guard import analyze_transactions, build_family_alert
from agents.gan_tester import GANTester, TestReport

from agents.llm import get_llm

from langchain_core.messages import HumanMessage, SystemMessage



st.set_page_config(page_title="JB Legacy", page_icon="🏮", layout="wide")

# API 키 가드 — 분석 도중 깊은 곳에서 터지지 않도록 시작 시점에 명확히 중단
if not os.getenv("OPENAI_API_KEY"):
    st.error(
        "OPENAI_API_KEY가 설정되지 않았습니다. "
        "프로젝트 루트의 .env 파일에 키를 입력한 뒤 다시 실행해 주세요 (.env.example 참고)."
    )
    st.stop()



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



_ANALYSIS_KEYWORDS = (
    "은퇴", "가게", "사업", "매각", "팔", "넘기", "승계", "물려", "상속", "증여",
    "세금", "절세", "권리금", "노후", "연금", "포트폴리오", "자산", "현금흐름",
    "월수령", "생활비", "어떻게", "얼마", "정리",
)


def _is_analysis_request(query: str) -> bool:
    # 키워드 fast-path: 핵심 재무 키워드가 있으면 LLM 분류 없이 분석으로 처리
    # (자연스러운 문장 "은퇴하고 싶어요", "어떻게 해야 할까요"가 대화로 오분류되는 것 방지)
    if any(kw in query for kw in _ANALYSIS_KEYWORDS):
        return True

    llm = get_llm("fast")

    resp = llm.invoke([HumanMessage(content=(

        "다음 메시지가 사업 매각·승계·세금·노후 설계 등 재무 분석을 요청하는 것인지 판단하세요.\n"

        "분석 요청 예시: 세금 얼마야, 승계하면 어때, 팔면 얼마 남아, 노후 준비, 권리금, 포트폴리오 등\n"

        "일반 대화 예시: 인사, 감사, 안녕, 네, 아니오, 짧은 감탄사 등\n"

        f"메시지: {query}\n"

        "ANALYSIS 또는 CHAT 중 하나만 반환하세요."

    ))]).content.strip()

    return resp == "ANALYSIS"





def _is_followup(query: str) -> bool:

    llm = get_llm("fast")

    resp = llm.invoke([HumanMessage(content=(

        "다음 질문이 이미 완료된 사업 엑시트 분석에 대한 후속 질문인지 판단하세요.\n"

        "후속 질문 예시: 결과 설명, 수치 재질문, 이유 설명, 포트폴리오/세금/시나리오 해석 요청, 왜/더/자세히/어떻게/비교 키워드\n"

        "새 분석 예시: 아무 분석도 없는 첫 질문, 완전히 다른 주제로 처음부터 새로 계산하는 요청\n"



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

    llm = get_llm("smart", temperature=0.1)

    answer = llm.invoke([

        SystemMessage(content=(

            "JB Legacy AI 어드바이저입니다. 이전 분석 결과를 참고하여 후속 질문에 답하세요.\n"

            "마크다운 기호(*, **, #, `)를 사용하지 마세요. 숫자는 정확히 인용하세요.\n"

            "특정 상품·시나리오를 '최선'이라고 단정하지 마세요(추천 정도는 가능).\n"

            "답변은 5~7줄 이내로."

        )),

        HumanMessage(content=f"{context}\n\n사용자 질문: {query}"),

    ]).content

    # 금소법 면책 고지를 코드로 강제 삽입 (LLM 누락 방지 → 검수 FAIL 루프 차단)
    return answer.rstrip() + _COMPLIANCE_DISCLAIMER





_COMPLIANCE_DISCLAIMER = (
    "\n\n[유의사항]\n"
    "본 내용의 세금·수익 수치는 추정치이며 실제와 다를 수 있습니다. 세무사 상담을 권장합니다. "
    "투자·연금 상품은 원금 손실 가능성이 있으니 가입 전 위험등급을 확인하시기 바랍니다. "
    "최종 결정은 고객 본인 또는 담당 PB·세무사가 함께 하시기 바랍니다."
)


_COMPLIANCE_RULES = """

1. 세금 추정치는 '약', '예상', '추정' 등 불확실성을 명시해야 합니다.

2. '세무사 상담을 권장합니다' 문구가 반드시 포함되어야 합니다.

3. 투자 추천 시 '원금 손실 가능성'과 위험등급을 명시해야 합니다.

4. 최종 결정은 고객 본인 또는 담당 PB·세무사가 해야 함을 명시해야 합니다.

5. 특정 상품을 단정적으로 '최선'이라고 말해서는 안 됩니다.

"""





def _run_compliance(text: str) -> tuple[bool, str]:

    llm = get_llm("fast")

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




def _scenario_snapshot(result: dict) -> dict:

    """시나리오별 (월수령, 생존확률) 캡처 — what-if 변경 전후 비교용."""

    snap = {}

    if not result:

        return snap

    portfolio = result.get("retirement_portfolio", {})

    pairs = [
        ("A안", portfolio.get("scenario_sale")),
        ("B안", portfolio.get("scenario_succession")),
        ("C안", portfolio.get("scenario_hybrid")),
        ("D안", result.get("negotiation_result", {}).get("scenario_negotiated")),
    ]

    for label, s in pairs:

        if not s:

            continue

        snap[label] = {
            "monthly":  s.get("monthly_income", {}).get("합계", 0),
            "survival": s.get("monte_carlo", {}).get("survival_probability"),
        }

    return snap




def _build_whatif_diff(before: dict, after: dict) -> str:

    """변경 전후 수치 비교 블록 생성. 비교 대상 없으면 빈 문자열."""

    if not before or not after:

        return ""

    lines = []

    for label, b in before.items():

        a = after.get(label)

        if not a:

            continue

        d_m = a["monthly"] - b["monthly"]

        line = f"{label} 월수령 {b['monthly']:,}원 → {a['monthly']:,}원 ({d_m:+,}원)"

        if b.get("survival") is not None and a.get("survival") is not None:

            line += f" / 생존확률 {b['survival']}% → {a['survival']}%"

        lines.append(line)

    if not lines:

        return ""

    return "\n\n[변경 전후 비교]\n" + "\n".join(lines)





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

                    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')

                    for note in proj.get("notes", []):

                        st.caption(f"• {note}")



            cont = scenario.get("business_continuity")

            if cont:

                with st.expander("가업 지속 가치 (자녀·가족 관점)"):

                    st.caption(f"상권 트렌드: {cont['market_trend']} (연 {cont['annual_growth_rate']*100:+.0f}%)")

                    st.metric("자녀 10년 누적 수익", f"{cont['daughter_cumulative_income']:,}원")

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

    # ── 몬테카를로 생존 확률 (추천 시나리오 기준) ─────────────────────────
    _rec_scenario = (
        s_sale if "A" in recommended
        else s_succ if "B" in recommended
        else s_hybrid if "C" in recommended
        else s_sale
    )
    if _rec_scenario:
        mc = _rec_scenario.get("monte_carlo", {})
        if mc:
            sp = mc["survival_probability"]
            sp_color = "#16a34a" if sp >= 80 else "#f59e0b" if sp >= 60 else "#dc2626"
            mc1, mc2, mc3 = st.columns(3)
            mc1.markdown(
                f'<div style="background:#f9fafb;border:2px solid {sp_color};border-radius:10px;'
                f'padding:14px;text-align:center">'
                f'<div style="font-size:11px;color:#6b7280">몬테카를로 은퇴 생존 확률</div>'
                f'<div style="font-size:28px;font-weight:700;color:{sp_color}">{sp}%</div>'
                f'<div style="font-size:11px;color:#9ca3af">{mc["simulations"]:,}회 시뮬레이션 · {mc["target_age"]}세까지</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            mc2.metric("중앙값 잔여자산 (100세)", f"{mc['median_final_capital']:,}원")
            mc3.metric("하위 10% 시나리오", f"{mc['p10_final_capital']:,}원",
                       help="최악 10% 경우의 100세 잔여자산")

    # ── 시나리오별 생존 확률 곡선 + 고갈 연령 분포 (CPP 의료비 쇼크 모형) ──
    mc_comp = portfolio.get("monte_carlo_comparison", {})
    _curves = {
        f"{label}안": data["survival_curve"]
        for label, data in mc_comp.items()
        if not label.startswith("_") and data
    }
    if _curves:
        import pandas as pd
        st.markdown(
            '<p class="section-label" style="margin-top:24px">은퇴 자산 생존 확률 — '
            '의료비 쇼크 몬테카를로'
            '<span style="font-size:10px;background:#ede9fe;color:#5b21b6;'
            'padding:2px 6px;border-radius:4px;margin-left:6px">CPP 모형</span></p>',
            unsafe_allow_html=True,
        )
        ch1, ch2 = st.columns(2)
        with ch1:
            curve_df = pd.DataFrame({k: pd.Series(v) for k, v in _curves.items()})
            curve_df.index.name = "나이"
            st.line_chart(curve_df, x_label="나이(세)", y_label="생존 확률(%)", height=260)
            st.caption("연령별 자산 미고갈 확률 (시나리오 간 동일 난수 통제 비교)")
        with ch2:
            ruin_df = pd.DataFrame({
                f"{label}안": data["ruin_age_brackets"]
                for label, data in mc_comp.items()
                if not label.startswith("_") and data
            })
            st.bar_chart(ruin_df, x_label="고갈 연령 구간", y_label="고갈 확률(%)", height=260)
            st.caption("자산 고갈 시점 분포 (구간별 %)")
        _model = mc_comp.get("_model", {})
        with st.expander("의료비 쇼크 모형 설명"):
            st.caption(
                "복합 포아송 과정(CPP): 긴급 의료비가 연평균 "
                f"{_model.get('lam_annual', 0.25)}회(4년에 1회 꼴) 발생, "
                f"1회 평균 {_model.get('avg_shock', 30_000_000):,}원(지수분포) 지출을 가정합니다. "
                f"{_model.get('sims', 1000):,}회 경로 시뮬레이션이며, "
                "모든 시나리오가 동일한 시장 국면과 쇼크 타이밍을 겪도록 통제(CRN)했습니다. "
                "순인출액 = 목표 생활비 − (국민연금 + 주택연금 + 자문료) 기준이고, "
                "수익률 가정은 A 연 4.5%(변동성 6.0%), B 3.0%(1.5%), C 3.8%(4.0%)입니다. "
                "주택연금 활용·목표 생활비 조정 시 생존 확률이 크게 달라집니다."
            )

    st.caption("유의: 펀드·연금 상품은 원금 손실 가능성이 있습니다. B안은 순수익 20%, C안은 순수익 10%를 자녀에게서 10년간 자문료로 수취하는 현실적 타협안을 가정했습니다.")




def _negotiation_section(negotiation_result: dict):
    """이과장이 제안한 D안(합의안) 섹션 — 이사장 분석 패널에 표시."""

    if not negotiation_result:

        return

    scenario = negotiation_result.get("scenario_negotiated", {})

    cond     = negotiation_result.get("daughter_conditions", {})

    summary  = negotiation_result.get("deal_summary", "")

    if not scenario:

        return

    st.divider()

    st.markdown(
        '<p class="section-label" style="color:#16a34a">D안 — 자녀(이과장)의 협상 제안</p>',
        unsafe_allow_html=True,
    )

    msg = cond.get("message", "")

    if msg:

        st.markdown(
            f'<div style="background:#f0fdf4;border-left:4px solid #16a34a;'
            f'padding:12px 16px;border-radius:0 8px 8px 0;font-size:14px;'
            f'color:#14532d;margin-bottom:16px">'
            f'이과장의 한마디: <em>"{msg}"</em></div>',
            unsafe_allow_html=True,
        )

    dc1, dc2, dc3 = st.columns(3)

    dc1.metric("승계 비율", f"{cond.get('succession_rate', 0)*100:.0f}%")

    dc2.metric("자문료율", f"{cond.get('consulting_rate', 0)*100:.0f}%")

    dc3.metric("월 자문료", f"{cond.get('consulting_monthly', 0):,}원")

    m = scenario.get("monthly_income", {})

    surplus = scenario.get("surplus_monthly", 0)

    total_capital = scenario.get("total_capital", 0)

    mc1, mc2 = st.columns(2)

    mc1.metric(
        "아버지 월 수령합계 (D안)",
        f"{m.get('합계', 0):,}원",
        delta=f"목표 대비 {surplus:+,}원",
        delta_color="normal" if surplus >= 0 else "inverse",
    )

    mc2.metric("운용자산", f"{total_capital:,}원")

    # 자산 배분 내역
    alloc = scenario.get("allocation", {})
    if alloc and total_capital > 0:
        st.divider()
        st.caption("자산 배분")
        for k, v in alloc.items():
            pct = v / total_capital
            st.progress(pct, text=f"{k}  {v:,}원 ({pct*100:.0f}%)")

    # 월 수령 항목별 상세
    if m:
        st.markdown("**월 수령 내역**")
        for k, v in m.items():
            if k != "합계":
                st.caption(f"{k}: {v:,}원")

    rationale = scenario.get("portfolio_rationale", "")
    if rationale:
        with st.expander("D안 — 포트폴리오 구성 이유"):
            st.text(rationale)

    if summary:

        st.markdown(
            f'<div class="rationale-box" style="margin-top:12px">{summary}</div>',
            unsafe_allow_html=True,
        )

        _neg_cfb = negotiation_result.get("compliance_feedback", "")

        if _neg_cfb:

            _neg_cls = "compliance-ok" if _neg_cfb.startswith("✅") else "compliance-err"

            st.markdown(f'<p class="{_neg_cls}">{_neg_cfb.replace("✅", "").replace("⚠️", "").strip()}</p>', unsafe_allow_html=True)

    cont = scenario.get("business_continuity", {})

    if cont:

        with st.expander("D안 — 가업 지속 가치 (자녀·가족 관점)"):

            st.caption(f"상권 트렌드: {cont.get('market_trend', '보합')} (연 {cont.get('annual_growth_rate', 0)*100:+.0f}%)")

            st.metric("자녀 10년 누적 수익", f"{cont.get('daughter_cumulative_income', 0):,}원")

            st.metric("10년 후 권리금 추정", f"{cont.get('future_goodwill', 0):,}원",
                      delta=cont.get("future_grade", ""))

            st.metric("가족 총자산 증가", f"{cont.get('family_asset_gain', 0):,}원")

    proj = scenario.get("long_term_projection", {})

    milestones = proj.get("milestones", {})

    if milestones:

        with st.expander("D안 — 장기 재정 전망"):

            import pandas as pd

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

            st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')





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

        st.caption(f"유의사항: {sections['주의사항']}")





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





def _render_analysis_result(result, selected_user):
    """분석 결과를 서브탭으로 분리 렌더링 (세금 / 노후 설계 / 가족 협상 / 상담·리포트)."""
    recommended = result.get("recommended_scenario", "")
    neg = result.get("negotiation_result", {})
    t_tax, t_wm, t_nego, t_more = st.tabs(["세금 비교", "노후 설계", "가족 협상(D안)", "상담·리포트"])

    with t_tax:
        _tax_cards(result.get("tax_comparison", {}))

    with t_wm:
        _portfolio_section(result.get("retirement_portfolio", {}), recommended)

    with t_nego:
        if neg:
            _negotiation_section(neg)
        else:
            st.caption("자녀(이과장)가 협상 조건을 제안하면 합의안(D안)이 여기에 표시됩니다.")
        if st.button("자녀(이과장)에게 공유 / 협상 시작", width='stretch', key="share_child"):
            st.session_state["split_result"] = result
            st.session_state["child_view_active"] = True
            st.rerun()

    with t_more:
        final_for_tts = result.get("final_response_raw") or result.get("final_response", "")
        if final_for_tts:
            _voice_briefing_section(final_for_tts)
        _booking_section(result.get("booking_result", {}))
        _contract_manager_section(result)
        try:
            pdf_cache = st.session_state.get("pdf_cache", {})
            pdf_key = (
                f"{selected_user}|{st.session_state.get('last_query', '')}|"
                f"{len(result.get('final_response_raw') or result.get('final_response', ''))}|"
                f"{bool(result.get('negotiation_result'))}"
            )
            if pdf_cache.get("key") != pdf_key:
                from tools.pdf_report import build_pdf_report
                pdf_cache = {"key": pdf_key, "data": build_pdf_report(
                    result, st.session_state.get("life_inputs", {}), USERS.get(selected_user, {}))}
                st.session_state["pdf_cache"] = pdf_cache
            st.download_button("PB 상담용 PDF 리포트 다운로드", data=pdf_cache["data"],
                               file_name="JB_Legacy_분석리포트.pdf", mime="application/pdf",
                               width='stretch', key="pdf_dl")
        except Exception as pdf_err:
            st.caption(f"PDF 리포트를 생성할 수 없습니다: {pdf_err}")
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
        st.markdown(f'<p class="{cls}">{cfb.replace("✅", "").replace("⚠️", "").strip()}</p>',
                    unsafe_allow_html=True)



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

        # ── 이과장 협상 제안 폼 ──────────────────────────────────────────
        st.divider()

        neg_existing = result.get("negotiation_result", {})

        if neg_existing:

            cond = neg_existing.get("daughter_conditions", {})

            st.success(
                f"협상안(D안)이 이미 제안되었습니다 "
                f"(승계 {cond.get('succession_rate',0)*100:.0f}% / "
                f"자문료 {cond.get('consulting_rate',0)*100:.0f}%)"
            )

            st.caption(f"자녀의 한마디: \"{cond.get('message','')}\"")

            if st.button("협상안 다시 제안하기", key="renegotiate"):

                st.session_state["show_negotiation_form"] = True

                st.rerun()

        else:

            st.session_state.setdefault("show_negotiation_form", True)



        if st.session_state.get("show_negotiation_form", True) and not neg_existing:

            st.markdown("#### 이과장의 협상 제안")

            st.caption("아버지의 시나리오를 검토하고 내 조건을 제안해보세요.")

            with st.form("daughter_negotiation_form"):

                col_a, col_b = st.columns(2)

                with col_a:

                    succession_pct = st.slider(
                        "승계 의향 — 내가 가게를 이어받을 비율",
                        min_value=0, max_value=100, value=70, step=5, format="%d%%",
                    )

                with col_b:

                    consulting_pct = st.slider(
                        "자문료 — 순이익 대비 아버지께 드릴 비율",
                        min_value=5, max_value=30, value=20, step=5, format="%d%%",
                    )

                daughter_msg = st.text_input(
                    "아버지께 한마디 (선택)",
                    placeholder="예: 제가 최선을 다해 가게를 지키겠습니다.",
                )

                submitted = st.form_submit_button("협상안 제안하기 →", type="primary", width='stretch')

                if submitted:

                    with st.spinner("D안(합의안) 생성 중..."):

                        neg_state = {
                            **result,
                            "daughter_inputs": {
                                "succession_rate":  succession_pct / 100,
                                "consulting_rate":  consulting_pct / 100,
                                "message":          daughter_msg,
                            },
                        }

                        neg_out = negotiation_agent(neg_state)

                        # D안 합의문에 면책 고지를 코드로 강제 삽입 후 검수 (FAIL 루프 방지)
                        _nr = neg_out.get("negotiation_result", {})
                        _deal = _nr.get("deal_summary", "")

                        if _deal:

                            _deal = _deal.rstrip() + _COMPLIANCE_DISCLAIMER

                            _nr["deal_summary"] = _deal

                            _ok, _fb = _run_compliance(_deal)

                            _nr["compliance_feedback"] = _fb

                    merged = {**result, **neg_out}

                    st.session_state["last_result"]  = merged

                    st.session_state["split_result"] = merged

                    st.session_state["show_negotiation_form"] = False

                    st.success("D안(합의안)이 아버지 화면에 전달되었습니다!")

                    st.rerun()

    else:

        st.info("Scene 1 또는 Scene 3을 먼저 실행해주세요.")





def _voice_briefing_section(final_response: str):
    """OpenAI TTS 기반 AI PB 음성 브리핑 — 시니어 배리어 프리 UI."""
    import io
    st.markdown('<p class="section-label">AI PB 음성 브리핑 <span style="font-size:10px;background:#ede9fe;color:#5b21b6;padding:2px 6px;border-radius:4px;margin-left:6px">시니어 UI</span></p>', unsafe_allow_html=True)
    if st.button("AI PB의 음성 브리핑 듣기", width='stretch', key="tts_btn"):
        with st.spinner("음성 생성 중... (약 5~10초)"):
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            # 종합 의견 핵심만 추출 (800자 이내 — TTS 비용·속도 최적화)
            text = _strip_md(final_response)[:800]
            speech = client.audio.speech.create(
                model="tts-1",
                voice="nova",   # 밝고 친근한 여성 목소리
                input=f"안녕하세요, JB Legacy AI 어드바이저입니다. {text}",
                response_format="mp3",
            )
            audio_bytes = io.BytesIO(speech.content)
        st.audio(audio_bytes, format="audio/mp3", autoplay=False)
        st.caption("본 음성 브리핑은 AI가 생성한 참고용 정보입니다. 최종 결정은 담당 PB·세무사와 상담하시기 바랍니다.")


_GRADE_COLOR = {"정상": "#16a34a", "주의": "#f59e0b", "경보": "#dc2626"}


def _early_warning_section(user_id: str, monthly_profit: int = 0):
    """폐업 조기경보 대시보드 — 독립 패널 (DEMO MOCK)."""
    health = calc_health_score(user_id, monthly_profit_override=monthly_profit)
    if not health:
        return

    st.markdown(
        '<p class="section-label">경영 건강 대시보드 '
        '<span style="font-size:10px;background:#fef3c7;color:#92400e;'
        'padding:2px 6px;border-radius:4px;margin-left:6px">데모 데이터</span></p>',
        unsafe_allow_html=True,
    )

    score   = health["overall_score"]
    grade   = health["overall_grade"]
    gcolor  = _GRADE_COLOR[grade]

    sc1, sc2, sc3 = st.columns([1, 2, 1])
    with sc1:
        st.markdown(
            f'<div style="text-align:center;padding:16px;background:#f9fafb;'
            f'border-radius:12px;border:2px solid {gcolor}">'
            f'<div style="font-size:32px;font-weight:700;color:{gcolor}">{score}</div>'
            f'<div style="font-size:11px;color:#6b7280">종합 건강점수</div>'
            f'<div style="font-size:18px;font-weight:700;color:{gcolor}">{grade}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with sc2:
        for name, fdata in health["factors"].items():
            fc = _GRADE_COLOR[fdata["grade"]]
            st.markdown(
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'font-size:13px;margin:4px 0">'
                f'<span style="color:#374151">{name}</span>'
                f'<span style="color:{fc};font-weight:600">'
                f'{fdata["grade"]}  {fdata["value"]}'
                f'</span></div>',
                unsafe_allow_html=True,
            )
    with sc3:
        sig = health.get("suggest_exit_within_months")
        if sig:
            st.markdown(
                f'<div style="background:#fef2f2;border:1px solid #fca5a5;'
                f'padding:12px;border-radius:8px;text-align:center">'
                f'<div style="font-size:12px;color:#991b1b;font-weight:600">'
                f'엑시트 권고 시점</div>'
                f'<div style="font-size:22px;font-weight:700;color:#dc2626">'
                f'{sig}개월 이내</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background:#f0fdf4;border:1px solid #86efac;'
                'padding:12px;border-radius:8px;text-align:center">'
                '<div style="font-size:12px;color:#166534;font-weight:600">'
                '현재 상태</div>'
                '<div style="font-size:18px;font-weight:700;color:#16a34a">'
                '안정적 운영 중</div>'
                '</div>',
                unsafe_allow_html=True,
            )

    with st.expander("위험 요인 및 권고사항 보기"):
        for w in health["warnings"]:
            c = "#dc2626" if "심각" in w or "시급" in w else "#92400e" if "필요" in w or "높" in w else "#374151"
            st.markdown(f'<div style="font-size:13px;color:{c};margin:4px 0">• {w}</div>', unsafe_allow_html=True)

    trend = health.get("trend", {})
    if trend.get("history_10k"):
        with st.expander("24개월 매출 추이 차트"):
            import pandas as pd
            from datetime import date
            hist = trend["history_10k"]
            today = date.today()
            # hist[0]=최근월 → 역순으로 뒤집어 과거→최신 순으로 표시
            labels = []
            for i in range(len(hist) - 1, -1, -1):
                m = today.month - i
                y = today.year + (m - 1) // 12
                m = ((m - 1) % 12) + 1
                labels.append(f"{str(y)[2:]}.{m:02d}")
            df = pd.DataFrame({
                "월": labels,
                "매출(만원)": list(reversed(hist)),
            })
            st.line_chart(df.set_index("월")["매출(만원)"], height=200)
            tc1, tc2, tc3 = st.columns(3)
            tc1.metric("최근 6개월 평균", f"{trend['recent_6m_avg']//10000:,}만원")
            tc2.metric("전월 대비", f"{trend['mom_change_pct']:+.1f}%")
            tc3.metric("전년 대비", f"{trend['yoy_change_pct']:+.1f}%",
                       delta_color="normal" if trend['yoy_change_pct'] > 0 else "inverse")

    st.caption("본 데이터는 데모용 시뮬레이션입니다. 본선에서 JB카드 마이데이터 API 연동 예정.")


_TIMING_COLOR = {"정상": "#16a34a", "주의": "#f59e0b", "경보": "#dc2626"}


def _dynamic_valuation_section(user_id: str, monthly_profit: int = 0):
    """마이데이터 기반 권리금 동적 평가 & 엑시트 타이밍 — 독립 패널 (DEMO MOCK)."""
    dv = calc_dynamic_goodwill(user_id, monthly_profit=monthly_profit or None)
    if not dv:
        return

    st.markdown(
        '<p class="section-label">권리금 동적 평가 & 엑시트 타이밍 '
        '<span style="font-size:10px;background:#fef3c7;color:#92400e;'
        'padding:2px 6px;border-radius:4px;margin-left:6px">데모 데이터</span></p>',
        unsafe_allow_html=True,
    )

    static  = dv["static_goodwill"]
    dynamic = dv["dynamic_goodwill"]
    delta   = dv["delta_pct"]
    timing  = dv["exit_timing"]
    tc      = _TIMING_COLOR[timing["urgency"]]

    vc1, vc2, vc3 = st.columns(3)
    with vc1:
        st.metric("기존 단순 계산 권리금", f"{static:,}원",
                  help="월순이익 × 기준배수 (트렌드 미반영)")
    with vc2:
        st.metric(
            "마이데이터 보정 권리금",
            f"{dynamic:,}원",
            delta=f"{delta:+.1f}% (매출·경쟁·입지 반영)",
            delta_color="normal" if delta >= 0 else "inverse",
        )
    with vc3:
        st.markdown(
            f'<div style="background:#f9fafb;border:2px solid {tc};'
            f'padding:14px;border-radius:10px;text-align:center">'
            f'<div style="font-size:11px;color:#6b7280">엑시트 권고 시점</div>'
            f'<div style="font-size:16px;font-weight:700;color:{tc}">'
            f'{timing["recommendation"]}</div>'
            f'<div style="font-size:11px;color:{tc};margin-top:4px">'
            f'{timing["urgency"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with st.expander("배수 보정 상세 & 엑시트 근거"):
        mb = dv["multiplier_breakdown"]
        ec1, ec2 = st.columns(2)
        with ec1:
            st.caption(f"기준 배수: {dv['base_multiple']}개월")
            st.caption(f"최종 적용 배수: {dv['adjusted_multiple']}개월")
            for k, v in mb.items():
                color = "#16a34a" if v >= 1.0 else "#dc2626"
                st.markdown(
                    f'<div style="font-size:13px;color:{color}">• {k}: ×{v:.2f}</div>',
                    unsafe_allow_html=True,
                )
        with ec2:
            st.markdown(
                f'<div style="background:#f0fdf4;border-left:4px solid {tc};'
                f'padding:12px;border-radius:0 8px 8px 0;font-size:13px;color:#1a1a2e">'
                f'{timing["reason"]}</div>',
                unsafe_allow_html=True,
            )
        st.caption(f"적용 월순이익: {dv['monthly_profit_applied']:,}원 / 매출 추세: {dv['trend_direction']}")

    st.caption("본 권리금은 추정치입니다. 정확한 평가는 공인중개사·세무사 상담을 받으시기 바랍니다. 본선에서 JB카드 마이데이터 API 연동 예정.")


_STAR = "★"


def _youth_matching_section(user_id: str):
    """지역 청년 창업가 매칭 & JB 인수 대출 — 독립 패널 (DEMO MOCK)."""
    info = get_youth_matching_info(user_id)
    if not info or not info.get("candidates"):
        return

    st.markdown(
        '<p class="section-label">청년 창업가 매칭 & JB 인수 대출 '
        '<span style="font-size:10px;background:#fef3c7;color:#92400e;'
        'padding:2px 6px;border-radius:4px;margin-left:6px">데모 데이터</span></p>',
        unsafe_allow_html=True,
    )

    candidates = info["candidates"]
    goodwill   = info["goodwill"]
    cols       = st.columns(len(candidates))

    for col, c in zip(cols, candidates):
        with col:
            afford_color = "#16a34a" if c["can_afford"] else "#f59e0b"
            afford_text  = "인수 가능" if c["can_afford"] else f"자금 {c['funding_gap']:,}원 부족"
            st.markdown(
                f'<div style="border:1px solid #e5e7eb;border-radius:10px;padding:14px;">'
                f'<div style="font-weight:700;font-size:15px">{c["name"]} ({c["age"]}세)</div>'
                f'<div style="font-size:12px;color:#6b7280">{c["region"]} · 신뢰도 {_STAR * int(c["rating"]//1)} {c["rating"]}</div>'
                f'<div style="font-size:12px;margin:8px 0;color:#374151">{c["intro"]}</div>'
                f'<div style="font-size:12px;color:{afford_color};font-weight:600">{afford_text}</div>'
                f'<div style="font-size:11px;color:#9ca3af">자기자금 {c["budget"]:,}원'
                + (f'  +  대출 {c["loan_limit"]:,}원' if c["loan_eligible"] else "")
                + '</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with st.expander("JB 청년 창업 대출 상품 안내"):
        for p in info["loan_products"]:
            st.markdown(
                f'<div style="background:#eff6ff;border:1px solid #93c5fd;'
                f'padding:12px;border-radius:8px;margin-bottom:8px">'
                f'<b>{p["name"]}</b>  |  금리 {p["rate"]}  |  한도 {p["limit"]}<br>'
                f'<span style="font-size:12px;color:#374151">조건: {p["condition"]}</span><br>'
                f'<span style="font-size:12px;color:#5b21b6">{p["feature"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with st.expander("인수인계 절차 안내"):
        for step in info["transfer_steps"]:
            st.markdown(f'<div style="font-size:13px;color:#374151;margin:4px 0">{step}</div>',
                        unsafe_allow_html=True)

    st.caption("매칭 후보는 데모용 시뮬레이션입니다. 본선에서 JB카드 청년 창업 대출 DB 연동 예정.")


def _fraud_guard_section(user_id: str):
    """이상거래 탐지 + 소비흐름 분석 + 가족 알림 — 독립 패널 (DEMO MOCK)."""
    info = analyze_transactions(user_id)
    if not info:
        st.caption("분석할 거래내역이 없습니다.")
        return

    st.markdown(
        '<p class="section-label">거래 안심 — 소비흐름 & 이상거래 감시 '
        '<span style="font-size:10px;background:#fef3c7;color:#92400e;'
        'padding:2px 6px;border-radius:4px;margin-left:6px">데모 데이터</span></p>',
        unsafe_allow_html=True,
    )

    # ── 소비흐름 요약 (자산·연금·부동산·소비 통합 분석의 소비 축) ──
    sc1, sc2 = st.columns([1, 2])
    with sc1:
        st.metric("월평균 생활 지출", f"{info['monthly_spend_normal']:,}원",
                  help=f"최근 {info['period_days']}일 정상 거래 기준 (이상거래 제외)")
        st.caption(f"최근 {info['period_days']}일 거래 {info['tx_count']}건 분석")
    with sc2:
        import pandas as pd
        cat_df = pd.DataFrame({"월평균 지출(원)": info["category_monthly"]})
        st.bar_chart(cat_df, horizontal=True, height=220)

    # ── 이상거래 경보 ──
    alerts = info["alerts"]
    if not alerts:
        st.success(f"최근 {info['period_days']}일 동안 평소와 다른 거래가 발견되지 않았습니다.")
        return

    st.markdown(
        f'<div style="background:#fef2f2;border:2px solid #dc2626;border-radius:10px;'
        f'padding:12px 16px;margin:10px 0;font-size:14px;color:#991b1b;font-weight:700">'
        f'평소와 다른 거래 {len(alerts)}건이 감지되었습니다 '
        f'(합계 {sum(a["amount"] for a in alerts):,}원)</div>',
        unsafe_allow_html=True,
    )

    for a in alerts:
        chips = " ".join(
            f'<span style="font-size:10px;background:#fee2e2;color:#991b1b;'
            f'padding:2px 6px;border-radius:4px;margin-right:4px">{r}</span>'
            for r in a["reasons"]
        )
        risk_color = "#dc2626" if a["risk"] == "높음" else "#f59e0b"
        st.markdown(
            f'<div style="border:1px solid #e5e7eb;border-left:4px solid {risk_color};'
            f'border-radius:8px;padding:10px 14px;margin-bottom:8px">'
            f'<div style="font-size:13px;font-weight:700">{a["merchant"]} — {a["amount"]:,}원 '
            f'<span style="color:{risk_color}">[위험도 {a["risk"]}]</span></div>'
            f'<div style="font-size:11px;color:#6b7280">{a["day_offset"]}일 전 {a["tx_time"]} · {a["channel"]}</div>'
            f'<div style="margin-top:6px">{chips}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── 가족 알림 (FamilyBridge 연계 스토리) ──
    sent_key = f"fraud_alert_sent_{user_id}"
    if st.session_state.get(sent_key):
        st.success("자녀(이과장)에게 이상거래 알림이 전송되었습니다.")
        with st.expander("전송된 알림 내용"):
            st.text(build_family_alert(USERS.get(user_id, {}), alerts))
    elif st.button("자녀(이과장)에게 이상거래 알림 보내기",
                   width='stretch', key="fraud_alert_btn", type="primary"):
        st.session_state[sent_key] = True
        st.rerun()

    st.caption("거래내역·탐지 결과는 데모용 시뮬레이션입니다. 본선에서 JB은행 실시간 FDS 연동 예정. "
               "보이스피싱 의심 시 지급정지 요청: 전북은행 063-250-5000 / 경찰청 112")


_CONTRACT_EVENT_ICON = {"start": "●", "tax": "●", "review": "●", "pension": "●", "end": "●"}


def _contract_manager_section(result: dict):
    """10년 자문료 자동이체 계약 & 생애주기 알림 — 독립 패널 (DEMO MOCK).

    D안(negotiation_result) 또는 B/C안의 consulting_monthly 값이 있을 때만 표시.
    """
    neg    = result.get("negotiation_result", {})
    cond   = neg.get("daughter_conditions", {}) if neg else {}
    monthly = cond.get("consulting_monthly", 0)
    rate    = cond.get("consulting_rate", 0)

    if not monthly:
        # 추천 시나리오에 자문료가 있을 때만 표시.
        # A안(완전 매각)은 자문료가 없으므로 이 섹션을 띄우지 않는다.
        recommended = result.get("recommended_scenario", "")
        port = result.get("retirement_portfolio", {})
        scen = None
        if recommended == "B":
            scen = port.get("scenario_succession")
        elif recommended == "C":
            scen = port.get("scenario_hybrid")
        if scen:
            monthly = scen.get("monthly_income", {}).get("자문료·급여", 0)

    if not monthly:
        return

    user_id = result.get("user_profile", {}).get("user_id", "lee_sajang")
    plan    = build_contract_plan(user_id, monthly, rate)

    st.divider()
    st.markdown(
        '<p class="section-label">10년 자문료 자동이체 & 생애주기 알림 '
        '<span style="font-size:10px;background:#fef3c7;color:#92400e;'
        'padding:2px 6px;border-radius:4px;margin-left:6px">데모 데이터</span></p>',
        unsafe_allow_html=True,
    )

    cc1, cc2, cc3, cc4 = st.columns(4)
    cc1.metric("월 자문료", f"{monthly:,}원")
    cc2.metric("10년 총 수령 (세전)", f"{plan['total_gross']:,}원")
    cc3.metric("10년 총 수령 (세후)", f"{plan['total_net']:,}원")
    cc4.metric("연간 원천징수 추정", f"{plan['tax_annual_estimate']:,}원")

    with st.expander("생애주기 이벤트 타임라인"):
        for ev in plan["lifecycle_events"]:
            icon = _CONTRACT_EVENT_ICON.get(ev["type"], "●")
            st.markdown(
                f'<div style="display:flex;gap:12px;align-items:flex-start;margin:6px 0">'
                f'<span style="font-size:14px">{icon}</span>'
                f'<div>'
                f'<span style="font-size:12px;color:#9ca3af">{ev["date"]} (만 {ev["age"]}세)</span><br>'
                f'<span style="font-size:13px;color:{ev["color"]};font-weight:600">{ev["event"]}</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    with st.expander("연도별 수령 스케줄"):
        import pandas as pd
        rows = [
            {
                "연도": f'{s["year"]}년차',
                "나이": f'만 {s["age"]}세',
                "연 수령(세전)": f'{s["annual_gross"]:,}원' if s["annual_gross"] else "계약 종료",
                "연 수령(세후)": f'{s["annual_net"]:,}원' if s["annual_net"] else "-",
                "누적 수령(세후)": f'{s["cumulative"]:,}원',
            }
            for s in plan["schedule"]
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')

    st.markdown(
        f'<div style="background:#eff6ff;border:1px solid #93c5fd;'
        f'padding:10px 14px;border-radius:8px;font-size:12px;color:#1e3a5f">'
        f'{plan["jb_auto_transfer_note"]}</div>',
        unsafe_allow_html=True,
    )
    st.caption("자문료 세금은 추정치입니다. 본선에서 JB은행 자동이체 API 연동 예정.")


_SEVERITY_COLOR = {"심각": "#dc2626", "보통": "#f59e0b", "경미": "#6b7280"}
_SEVERITY_ICON  = {"심각": "", "보통": "", "경미": ""}
_VERDICT_COLOR  = {"통과": "#16a34a", "조건부통과": "#f59e0b", "재생성필요": "#dc2626"}
_VERDICT_ICON   = {"통과": "", "조건부통과": "", "재생성필요": ""}


def _gan_test_section(result: dict | None):
    """GAN 스타일 AI 응답 품질 테스트 — Critic · Defender · Judge."""
    st.markdown(
        '<p class="section-label">GAN 품질 테스트 '
        '<span style="font-size:10px;background:#ede9fe;color:#5b21b6;'
        'padding:2px 6px;border-radius:4px;margin-left:6px">Critic vs Defender vs Judge</span></p>',
        unsafe_allow_html=True,
    )

    if not result:
        st.info("먼저 채팅창에서 분석을 실행한 뒤 GAN 테스트를 시작하세요.")
        return

    final_response = result.get("final_response_raw") or result.get("final_response", "")
    query          = result.get("query", "")

    if not final_response:
        st.warning("분석 결과 텍스트가 없습니다. 먼저 재무 분석 질문을 입력해 주세요.")
        return

    with st.expander("테스트 대상 AI 응답 미리보기"):
        st.text(final_response[:600] + ("..." if len(final_response) > 600 else ""))

    col_r, col_btn = st.columns([1, 2])
    with col_r:
        rounds = st.selectbox("토론 라운드", [1, 2], index=0, key="gan_rounds")
    with col_btn:
        st.markdown("")
        run_btn = st.button("GAN 테스트 시작", type="primary", width='stretch', key="gan_run")

    # 이전 결과 캐시 — 같은 응답+라운드면 재실행 안 함
    cache_key = f"{hash(final_response)}_{rounds}"
    cached_report: TestReport | None = st.session_state.get("gan_report") if st.session_state.get("gan_cache_key") == cache_key else None

    if run_btn and not cached_report:
        progress_ph = st.empty()
        with st.spinner("GAN 테스트 진행 중... (약 30~60초)"):
            progress_ph.info("공격자(Critic) 분석 중...")
            tester = GANTester(rounds=rounds)
            report = tester.run(query=query, ai_response=final_response)
        progress_ph.empty()
        st.session_state["gan_report"]    = report
        st.session_state["gan_cache_key"] = cache_key
        cached_report = report
        st.rerun()

    if not cached_report:
        return

    report: TestReport = cached_report
    fs = report.final_score

    # ── 최종 점수 헤더 ────────────────────────────────────────────────────
    total  = fs.total_score
    vc     = _VERDICT_COLOR.get(fs.verdict, "#888")
    vi     = _VERDICT_ICON.get(fs.verdict, "")
    sc_col = "#16a34a" if total >= 80 else "#f59e0b" if total >= 60 else "#dc2626"

    r1, r2, r3 = st.columns(3)
    r1.markdown(
        f'<div style="text-align:center;padding:18px;background:#f9fafb;'
        f'border:2px solid {sc_col};border-radius:12px">'
        f'<div style="font-size:11px;color:#6b7280">종합 점수</div>'
        f'<div style="font-size:36px;font-weight:700;color:{sc_col}">{total}</div>'
        f'<div style="font-size:11px;color:#9ca3af">/ 100</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    r2.markdown(
        f'<div style="text-align:center;padding:18px;background:#f9fafb;'
        f'border:2px solid {vc};border-radius:12px">'
        f'<div style="font-size:11px;color:#6b7280">최종 판정</div>'
        f'<div style="font-size:22px;font-weight:700;color:{vc}">{vi} {fs.verdict}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    r3.markdown(
        f'<div style="padding:18px;background:#f9fafb;border-radius:12px;border:1px solid #e5e7eb">'
        f'<div style="font-size:11px;color:#6b7280;margin-bottom:6px">카테고리별 점수</div>'
        + "".join(
            f'<div style="display:flex;justify-content:space-between;font-size:12px;margin:3px 0">'
            f'<span style="color:#374151">{s.category}</span>'
            f'<span style="font-weight:600;color:{"#16a34a" if s.score>=80 else "#f59e0b" if s.score>=60 else "#dc2626"}">{s.score}점</span>'
            f'</div>'
            for s in fs.scores
        )
        + f'</div>',
        unsafe_allow_html=True,
    )

    # ── 판정 요약 ─────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="background:#f8f6ff;border-left:4px solid #5b21b6;'
        f'padding:14px 18px;border-radius:0 8px 8px 0;font-size:14px;'
        f'color:#1a1a2e;margin:16px 0;white-space:pre-wrap">{fs.summary}</div>',
        unsafe_allow_html=True,
    )

    # ── 핵심 개선 사항 ────────────────────────────────────────────────────
    if fs.key_improvements:
        st.markdown('<p class="section-label" style="margin-top:16px">핵심 개선 사항</p>', unsafe_allow_html=True)
        for imp in fs.key_improvements:
            st.markdown(
                f'<div style="background:#fef3c7;border-left:3px solid #f59e0b;'
                f'padding:8px 12px;border-radius:0 6px 6px 0;font-size:13px;'
                f'color:#92400e;margin:4px 0">{imp}</div>',
                unsafe_allow_html=True,
            )

    # ── 토론 과정 ─────────────────────────────────────────────────────────
    for rd in report.rounds:
        with st.expander(f"Round {rd.round_num} — 공격 vs 방어 상세"):
            st.markdown("**공격자 (Critic)**")
            for p in rd.critique.points:
                sev_c = _SEVERITY_COLOR.get(p.severity, "#888")
                sev_i = _SEVERITY_ICON.get(p.severity, "")
                st.markdown(
                    f'<div style="background:#fef2f2;border-left:3px solid {sev_c};'
                    f'padding:10px 14px;border-radius:0 6px 6px 0;margin:6px 0">'
                    f'<div style="font-size:12px;font-weight:700;color:{sev_c}">'
                    f'{sev_i} {p.category} — {p.severity}</div>'
                    f'<div style="font-size:13px;color:#1a1a2e;margin-top:4px">{p.issue}</div>'
                    f'<div style="font-size:11px;color:#6b7280;margin-top:4px">개선: {p.suggestion}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.markdown(
                f'<div style="background:#fff1f2;border:1px solid #fca5a5;'
                f'padding:10px 14px;border-radius:8px;font-size:13px;color:#7f1d1d;margin-top:8px">'
                f'전체 약점: {rd.critique.overall_weakness}</div>',
                unsafe_allow_html=True,
            )

            st.markdown("")
            st.markdown("**방어자 (Defender)**")
            for d in rd.defense.rebuttals:
                st.markdown(
                    f'<div style="background:#f0fdf4;border-left:3px solid #16a34a;'
                    f'padding:10px 14px;border-radius:0 6px 6px 0;margin:6px 0">'
                    f'<div style="font-size:12px;font-weight:700;color:#16a34a">{d.category}</div>'
                    f'<div style="font-size:13px;color:#1a1a2e;margin-top:4px">{d.rebuttal}</div>'
                    f'<div style="font-size:11px;color:#6b7280;margin-top:4px">인정: {d.concession}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.markdown(
                f'<div style="background:#f0fdf4;border:1px solid #86efac;'
                f'padding:10px 14px;border-radius:8px;font-size:13px;color:#14532d;margin-top:8px">'
                f'전체 방어: {rd.defense.overall_justification}</div>',
                unsafe_allow_html=True,
            )

    if st.button("테스트 초기화", key="gan_reset"):
        st.session_state.pop("gan_report", None)
        st.session_state.pop("gan_cache_key", None)
        st.rerun()


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

        st.markdown('<p class="ob-logo">JB Legacy</p>', unsafe_allow_html=True)

        st.markdown(

            '<p class="ob-sub">평생 일군 가게, 가장 명예롭게 마무리하는<br>AI 가업승계·엑시트 에이전트</p>',

            unsafe_allow_html=True,

        )



        st.markdown('<p class="ob-group">사장님 페르소나</p>', unsafe_allow_html=True)

        _OWNER_LABELS = {
            "lee_sajang":   "이사장  62세 · 전주 · 30년 한정식  (3.1억 | 승계 유리)",
            "kim_soojang":  "김소장  58세 · 부산 · 5년 분식집   (0.9억 | 세금 미미)",
            "park_wonjang": "박원장  55세 · 강남 · 8년 카페     (11.2억 | 매각 유리)",
            "choi_daepyo":  "최대표  65세 · 수원 · 22년 한식뷔페 (10.1억 | 승계 유리)",
        }

        selected_owner = st.radio(
            "사장님",
            list(_OWNER_LABELS.keys()),
            format_func=lambda x: _OWNER_LABELS[x],
            label_visibility="collapsed",
        )

        st.markdown('<p class="ob-group">자녀 페르소나</p>', unsafe_allow_html=True)

        _CHILD_LABELS = {
            "none":        "— 자녀 없음 (사장님 단독 분석)",
            "lee_gwajang": "이과장  32세 · 서울 · 직장인 자녀",
        }

        selected_child = st.radio(
            "자녀",
            list(_CHILD_LABELS.keys()),
            format_func=lambda x: _CHILD_LABELS[x],
            label_visibility="collapsed",
        )

        selected_user = selected_child if selected_child != "none" else selected_owner



        # 자녀 페르소나 선택 시 입력 폼 불필요 — 바로 이동

        if USERS.get(selected_user, {}).get("type") == "child":

            st.info("이과장 화면은 아버지의 분석 결과를 공유 받아 열람합니다.\n이사장이 먼저 분석을 완료해야 합니다.")

            st.markdown("")

            if st.button("이과장 화면 열기 →", type="primary", width='stretch'):

                st.session_state.update({

                    "selected_user": "lee_gwajang",

                    "life_inputs": {},

                    "step": 2,

                })

                st.rerun()

        else:

            st.markdown('<p class="ob-group">월 순이익 입력</p>', unsafe_allow_html=True)

            _default_profit = USERS.get(selected_owner, {}).get("business", {}).get("monthly_profit", 0)

            _profit_mode = st.radio(
                "입력 방식",
                ["최근 3개월 직접 입력", "연간 순이익 ÷ 12"],
                horizontal=True,
                label_visibility="collapsed",
            )

            if _profit_mode == "최근 3개월 직접 입력":
                pc1, pc2, pc3 = st.columns(3)
                with pc1:
                    _m1 = st.number_input("지난달", min_value=0, value=_default_profit, step=100_000, format="%d", label_visibility="visible")
                with pc2:
                    _m2 = st.number_input("2개월 전", min_value=0, value=_default_profit, step=100_000, format="%d", label_visibility="visible")
                with pc3:
                    _m3 = st.number_input("3개월 전", min_value=0, value=_default_profit, step=100_000, format="%d", label_visibility="visible")
                _avg_profit = int((_m1 + _m2 + _m3) / 3) if (_m1 + _m2 + _m3) > 0 else _default_profit
            else:
                _annual = st.number_input("연간 순이익 (원)", min_value=0, value=_default_profit * 12, step=1_000_000, format="%d")
                _avg_profit = int(_annual / 12) if _annual > 0 else _default_profit

            st.caption(f"적용 월 순이익: **{_avg_profit:,}원** (현재는 참고용 — 추후 분석에 반영 예정)")

            st.markdown('<p class="ob-group">상황 입력</p>', unsafe_allow_html=True)

            r1c1, r1c2, r1c3 = st.columns(3)

            with r1c1:

                succession_input = st.selectbox("자녀 승계 의향", ["예", "아니오"])

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

            if st.button("분석 시작하기 →", type="primary", width='stretch'):

                st.session_state.update({

                    "selected_user":  selected_owner,

                    "life_inputs":    {

                        "succession":          succession_input,

                        "market_trend":        market_input,

                        "retirement_timeline": retirement_input,

                        "target_monthly":      _TARGET_OPTS[target_label],

                        "home_pension":        home_pension_input,

                        "monthly_profit":      _avg_profit,

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

    hc1, hc2 = st.columns([1, 8])

    with hc1:

        if st.button("← 처음으로"):

            # 처음으로 돌아갈 때 대화 기록 초기화

            st.session_state.update({"step": 1, "chat_history": [], "followup_compliance_fb": "", "feature_nav": ""})

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

            f'<span class="s2-title">JB Legacy</span>'

            f'<span class="s2-meta">{meta}</span>'

            f'</div>',

            unsafe_allow_html=True,

        )

    _feature_nav = ""

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

    # 사장님(이과장 제외)이 분석 결과를 가지면 부가 탭을 노출한다.
    # 경영건강·권리금·거래안심은 추천 무관하게 항상, 청년 매칭은 매각이 포함될 때만.
    _is_sale = (
        selected_user != "lee_gwajang"
        and _has_result
    )
    _recommended = (_result_preview or {}).get("recommended_scenario", "")
    # 청년 매칭(외부 인수)은 A(완전매각)·C(절충, 50% 매각)에서만. B(완전승계)·D(가족합의)는 제외.
    _show_youth = _is_sale and _recommended not in ("B", "D")

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

                '<div style="margin-top:24px;text-align:center;color:#9ca3af;">'

                '<div style="font-size:15px;font-weight:600;color:#374151;margin-bottom:8px">무엇이 궁금하신가요?</div>'

                '<div style="font-size:13px;line-height:1.8">'

                '매각 vs 승계 세금 비교 · 노후 현금흐름 시뮬레이션<br>'

                '권리금 계산 · PB 상담 예약'

                '</div></div>',

                unsafe_allow_html=True,

            )

        else:

            _chat_container = st.container(height=430, border=False)

            with _chat_container:

                for msg in chat_history:

                    with st.chat_message(msg["role"]):

                        st.write(msg["content"])



                followup_cfb = st.session_state.get("followup_compliance_fb", "")

                if followup_cfb:

                    cls = "compliance-ok" if followup_cfb.startswith("✅") else "compliance-err"

                    st.markdown(f'<p class="{cls}">{followup_cfb.replace("✅", "").replace("⚠️", "").strip()}</p>', unsafe_allow_html=True)



    if col_analysis is not None:

     with col_analysis:

        st.markdown('<div class="analysis-divider">', unsafe_allow_html=True)

        result = (

            st.session_state.get("last_result")

            if st.session_state.get("last_user") == selected_user

            else None

        )

        if _is_sale:

            _labels = ["분석 결과", "경영 건강", "권리금 평가"]
            if _show_youth:
                _labels.append("청년 매칭")
            _labels.append("거래 안심")
            _tabs = st.tabs(_labels)

            _t_analysis, _t_health, _t_goodwill = _tabs[0], _tabs[1], _tabs[2]
            _idx = 3
            if _show_youth:
                _t_youth = _tabs[_idx]; _idx += 1
            else:
                _t_youth = None
            _t_fraud = _tabs[_idx]

        else:

            st.markdown('<p class="panel-label">분석 결과</p>', unsafe_allow_html=True)

            _t_analysis = st.container()

            _t_health = _t_goodwill = _t_youth = _t_fraud = None

        _analysis_container = _t_analysis.container(height=500, border=False)

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

                                 _status.update(label=f"{NODE_LABELS.get(_node, _node)} 진행 중...")

                         _status.update(label="분석 완료", state="complete")

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



                 _render_analysis_result(result, selected_user)

         else:

             st.caption("질문을 입력하면 분석 결과가 여기에 표시됩니다.")

        if _t_health is not None:

            _life = st.session_state.get("life_inputs", {})

            _mp   = _life.get("monthly_profit", 0)

            with _t_health:

                _early_warning_section(selected_user, monthly_profit=_mp)

            with _t_goodwill:

                _dynamic_valuation_section(selected_user, monthly_profit=_mp)

            if _t_youth is not None:

                with _t_youth:

                    _youth_matching_section(selected_user)

            with _t_fraud:

                _fraud_guard_section(selected_user)

        st.markdown('</div>', unsafe_allow_html=True)




    # ── 채팅 입력 (페이지 하단 고정) ─────────────────────────────────────

    _FAMILY_KW  = ["딸", "아들", "자녀", "알려", "공유", "보내", "전달"]

    _BOOKING_KW = ["예약", "상담 받", "만나고", "방문", "세무사 연결", "PB 연결", "예약해", "상담해", "연결해"]



    # ── 음성 입력 (STT) — 시니어 배리어프리: 말로 질문하기 ──────────────────
    if is_slow:

        _audio = st.audio_input("버튼을 누르고 질문을 말씀해 주세요 (음성 입력)", key="stt_audio")

        if _audio is not None:

            import hashlib

            _audio_bytes = _audio.getvalue()

            _audio_hash  = hashlib.md5(_audio_bytes).hexdigest()

            # 같은 녹음이 rerun마다 재처리되지 않도록 해시로 1회만 변환
            if st.session_state.get("stt_last_hash") != _audio_hash:

                st.session_state["stt_last_hash"] = _audio_hash

                _stt_text = ""

                try:

                    with st.spinner("음성을 글로 바꾸는 중..."):

                        from openai import OpenAI

                        _stt_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                        _stt_text = _stt_client.audio.transcriptions.create(
                            model="whisper-1",
                            file=("voice.wav", _audio_bytes),
                            language="ko",
                        ).text.strip()

                except Exception as _stt_err:

                    st.caption(f"음성 인식에 실패했습니다. 아래에 직접 입력해 주세요. ({_stt_err})")

                if _stt_text:

                    st.session_state["pending_query"] = _stt_text

                    st.rerun()

    typed_q   = st.chat_input("궁금한 것을 물어보세요..." if not is_slow else "말씀해 주세요...")

    pending   = st.session_state.pop("pending_query", None)

    new_q     = typed_q or pending

    # 1단계: 새 입력이면 사용자 말풍선을 먼저 띄우고 즉시 rerun (분석 기다리는 동안 내 메시지 표시)
    if new_q:

        _ch = st.session_state.get("chat_history", [])

        _ch.append({"role": "user", "content": new_q})

        st.session_state["chat_history"] = _ch

        st.session_state["__run_query"] = new_q

        st.rerun()

    # 2단계: 직전에 표시한 사용자 메시지에 대해 실제 분석/응답 생성
    effective_q = st.session_state.pop("__run_query", None)



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
        # 사용자 메시지는 1단계에서 이미 추가됨



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

            reply = "이전 분석 결과를 자녀(이과장)에게 공유했습니다. 오른쪽 패널에서 확인하세요."

            chat_history.append({"role": "assistant", "content": reply})

            st.session_state["chat_history"] = chat_history

            st.rerun()



        elif has_analysis and cache_valid and (
            _param_result := detect_param_changes(effective_q, current_life)
        ) and _param_result[0]:

            # 파라미터 변경 감지 → life_inputs 업데이트 후 전체 재분석
            param_changes, change_desc = _param_result

            # 변경 전 수치 캡처 (재분석 후 전후 비교용)
            _prev_snapshot = _scenario_snapshot(cached)

            new_life = {**current_life, **param_changes}

            st.session_state["life_inputs"] = new_life

            change_summary = change_desc or "파라미터 변경: " + ", ".join(
                f"{k}={v}" for k, v in param_changes.items()
            )

            reply_prefix = f"설정을 변경하고 다시 분석합니다.\n{change_summary}\n\n"

            chat_history.append({"role": "assistant", "content": reply_prefix + "분석 중..."})

            st.session_state["chat_history"] = chat_history

            with st.status("파라미터 변경 후 재분석...", expanded=True) as _pstatus:

                result = {}

                for _node, _upd in stream_query(
                    selected_user, effective_q,
                    life_inputs=new_life,
                    thread_id=st.session_state["thread_id"],
                ):

                    if _node == "__done__":

                        result = _upd

                    else:

                        _pstatus.update(label=f"{NODE_LABELS.get(_node, _node)} 진행 중...")

                _pstatus.update(label="재분석 완료", state="complete")

            final    = result.get("final_response_raw") or result.get("final_response", "")

            sections = _parse_sections(final) if final else {}

            has_new_data = bool(result.get("tax_comparison") or result.get("retirement_portfolio"))
            if not has_new_data and cached:
                result = {**cached, **{k: v for k, v in result.items() if v}}

            summary  = (
                result.get("clarification_needed", "")
                or sections.get("최종 권고")
                or sections.get("종합 의견")
                or _strip_md(final)[:300]
                or "재분석이 완료되었습니다. 오른쪽 패널을 확인하세요."
            )

            _diff_block = _build_whatif_diff(_prev_snapshot, _scenario_snapshot(result))

            chat_history[-1]["content"] = reply_prefix + summary + _diff_block

            st.session_state.update({
                "last_result":            result,
                "last_user":              selected_user,
                "last_query":             effective_q,
                "last_life_inputs":       new_life,
                "chat_history":           chat_history,
                "followup_compliance_fb": "",
                "child_view_active":      False,
            })

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

            llm = get_llm("fast", temperature=0.3)

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

                        _status.update(label=f"{NODE_LABELS.get(_node, _node)} 진행 중...")

                _status.update(label="분석 완료", state="complete")



            final    = result.get("final_response_raw") or result.get("final_response", "")

            sections = _parse_sections(final) if final else {}

            # 새 분석 결과에 실질 데이터가 없으면(clarification_needed 등) 이전 결과 유지
            has_new_data = bool(result.get("tax_comparison") or result.get("retirement_portfolio"))
            if not has_new_data and cached:
                result = {**cached, **{k: v for k, v in result.items() if v}}

            clarify = result.get("clarification_needed", "")
            summary  = (
                clarify
                or sections.get("최종 권고")
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





