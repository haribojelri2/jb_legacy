"""Negotiation Agent — 이과장의 협상 조건으로 D안(합의안) 포트폴리오 생성."""

import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState
from agents.post_exit_wm import build_portfolio, home_pension_monthly
from tools.calculators import calc_goodwill_tax, estimate_business_value, calc_business_continuity

_SYSTEM = """\
당신은 JB Legacy AI 가족 협상 조율사입니다.
부모와 자녀의 협상 조건을 바탕으로 합의안(D안)을 3~4줄로 설명하세요.
마크다운 기호(*, **, #, `)를 절대 사용하지 마세요. 번호와 줄바꿈만 쓰세요.
자녀의 한마디를 반드시 언급하며, 어떤 부분에서 서로 이익이 되는지 짚어주세요."""


def negotiation_agent(state: AgentState) -> dict:
    daughter = state.get("daughter_inputs", {})
    if not daughter:
        return {}

    profile  = state.get("user_profile", {})
    biz      = profile.get("business", {})
    personal = profile.get("personal_assets", {})
    life     = profile.get("life_factors", {})
    age      = profile.get("age", 62)

    monthly_profit   = biz.get("monthly_profit", 4_500_000)
    years_operating  = biz.get("years_operating", 30)
    savings          = personal.get("savings", 0)
    pension          = personal.get("pension_monthly_expected", 900_000)
    annual_income    = monthly_profit * 12

    # 자녀의 협상 조건
    succession_rate  = float(daughter.get("succession_rate", 0.7))   # 자녀가 가져갈 비율 (0~1)
    consulting_rate  = float(daughter.get("consulting_rate", 0.20))  # 순이익 대비 자문료율
    daughter_message = daughter.get("message", "")

    # 사업체 가치
    explicit_goodwill = biz.get("goodwill")
    if explicit_goodwill:
        goodwill = explicit_goodwill
    else:
        goodwill = estimate_business_value(monthly_profit, years_operating)["goodwill_estimate"]

    # 부모가 현금화하는 비율 = (1 - succession_rate) × 권리금
    cash_goodwill = int(goodwill * (1 - succession_rate))
    partial_tax   = calc_goodwill_tax(cash_goodwill, other_income=annual_income).get("total_tax", 0)
    capital_d     = max(cash_goodwill - partial_tax, 0) + savings

    # 자녀가 매월 지급하는 자문료
    consulting_monthly = int(monthly_profit * consulting_rate)

    # 주택연금
    home_value     = personal.get("real_estate", 0)
    use_home_pen   = life.get("home_pension", "아니오") == "예"
    home_pension_m = home_pension_monthly(home_value, age) if use_home_pen and home_value > 0 else 0

    target_monthly = life.get("target_monthly", 3_000_000)
    market_trend   = life.get("market_trend", "보합")

    portfolio_d = build_portfolio(
        capital_d, pension,
        consulting_monthly=consulting_monthly,
        age=age,
        target_monthly=target_monthly,
        home_pension_monthly=home_pension_m,
        risk_profile="balanced",
    )

    # 가업 지속 가치 (자녀의 승계 비율 반영)
    continuity = calc_business_continuity(
        monthly_profit, years_operating,
        market_trend=market_trend,
        consulting_rate=consulting_rate,
    )
    portfolio_d["business_continuity"] = {
        **continuity,
        "daughter_cumulative_income": int(continuity["daughter_cumulative_income"] * succession_rate),
        "future_goodwill":            int(continuity["future_goodwill"] * succession_rate),
        "family_asset_gain":          int(
            continuity["daughter_cumulative_income"] * succession_rate
            + continuity["future_goodwill"] * succession_rate
        ),
    }

    # LLM 합의안 설명
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=os.getenv("OPENAI_API_KEY"))
    deal_summary = llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=(
            f"자녀의 협상 제안\n"
            f"  승계 의향: {succession_rate*100:.0f}% (사업체의 {succession_rate*100:.0f}%를 자녀가 이어받음)\n"
            f"  자문료: 순이익의 {consulting_rate*100:.0f}% = 월 {consulting_monthly:,}원 (10년간 부모에게 지급)\n"
            f"  자녀의 한마디: \"{daughter_message}\"\n\n"
            f"D안(합의안) 결과\n"
            f"  부모 현금화 금액: {cash_goodwill:,}원 (세후 {capital_d:,}원)\n"
            f"  부모 월 수령합계: {portfolio_d['monthly_income']['합계']:,}원\n"
            f"  자녀 10년 누적 수익: {portfolio_d['business_continuity']['daughter_cumulative_income']:,}원\n"
            f"  10년 후 권리금 추정: {portfolio_d['business_continuity']['future_goodwill']:,}원"
        )),
    ]).content

    return {
        "negotiation_result": {
            "scenario_negotiated": portfolio_d,
            "deal_summary":        deal_summary,
            "daughter_conditions": {
                "succession_rate":    succession_rate,
                "consulting_rate":    consulting_rate,
                "consulting_monthly": consulting_monthly,
                "message":            daughter_message,
            },
        }
    }
