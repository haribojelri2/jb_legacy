"""Post-Exit WM Agent — 3가지 시나리오별 노후 현금흐름 비교 (JB 실제 상품 기반)."""

from langchain_core.messages import HumanMessage, SystemMessage
from agents.llm import get_llm
from agents.state import AgentState
from tools.calculators import calc_goodwill_tax, estimate_business_value, calc_business_continuity
from tools.monte_carlo import (
    build_withdrawal_schedule,
    run_retirement_mc,
    run_scenario_comparison,
)
from data.jb_products import JB_PRODUCTS, get_products_for_retirement


# 카탈로그에서 카테고리별 최적 상품(최고 수익률) 선택
def _best(category_keyword: str) -> dict:
    candidates = [p for p in JB_PRODUCTS.values() if category_keyword in p["category"]]
    if not candidates:
        return {}
    return max(candidates, key=lambda p: p.get("expected_return") or p.get("max_rate") or p.get("base_rate") or 0)


def _rate(product: dict) -> float:
    """상품의 운용 금리(소수, 연율)."""
    r = product.get("expected_return") or product.get("max_rate") or product.get("base_rate") or 0
    return r / 100


def _annuity_pmt(principal: int, annual_rate: float, years: int) -> int:
    """즉시연금 월 수령액 — 원금+이자 균등 분할 지급 방식."""
    if principal <= 0 or annual_rate <= 0:
        return 0
    r = annual_rate / 12
    n = years * 12
    return int(principal * r / (1 - (1 + r) ** (-n)))


_ANNUITY_EXPENSE_RATIO = 0.07   # 즉시연금 사업비 약 7% (보험업계 평균)
_LONGEVITY_AGE        = 85      # 기대여명 기준 나이
_INFLATION_RATE       = 0.02    # 연 2% 물가상승률 가정

# 한국주택금융공사 주택연금 월지급금 (1억원 기준, 종신지급 정액형, 2025년 기준)
_HOME_PENSION_PER_100M = {
    55: 155_000, 56: 163_000, 57: 171_000, 58: 180_000, 59: 190_000,
    60: 201_000, 61: 211_000, 62: 221_000, 63: 232_000, 64: 240_000,
    65: 248_000, 66: 258_000, 67: 268_000, 68: 280_000, 69: 293_000,
    70: 308_000,
}


def home_pension_monthly(home_value: int, age: int) -> int:
    """주택연금 예상 월지급금 (HF 공사 공시 기준, 종신지급 정액형)."""
    age = max(55, min(age, 70))
    rate_per_100m = _HOME_PENSION_PER_100M.get(age, 221_000)
    return int(home_value / 100_000_000 * rate_per_100m)


def _long_term_projection(portfolio: dict, annuity_years: int = 10,
                          irp_years: int = 23, consulting_years: int = 10) -> dict:
    """연도별(0/5/10/15/20년) 명목·실질 월수령액 및 잔여원금 시뮬레이션."""
    income = portfolio.get("monthly_income", {})
    alloc  = portfolio.get("allocation", {})

    fund_m = annuity_m = deposit_m = irp_m = consulting_m = home_pension_m = 0
    pension_m = income.get("국민연금", 0)
    for k, v in income.items():
        if "월배당" in k:
            fund_m = v
        elif "즉시연금" in k:
            annuity_m = v
        elif "예금이자" in k:
            deposit_m = v
        elif "IRP" in k:
            irp_m = v
        elif "자문료" in k:
            consulting_m = v
        elif "주택연금" in k:
            home_pension_m = v

    fund_cap = annuity_cap = deposit_cap = irp_cap = 0
    for name, amt in alloc.items():
        if "월배당" in name:
            fund_cap = amt
        elif "즉시연금" in name:
            annuity_cap = amt
        elif "예금" in name:
            deposit_cap = amt
        elif "IRP" in name or "퇴직연금" in name:
            irp_cap = amt

    milestones = {}
    for yr in [0, 5, 10, 15, 20]:
        ann_on = yr < annuity_years
        irp_on = yr < irp_years
        consulting_on = yr < consulting_years
        
        # 국민연금은 물가상승률(2%)을 반영하여 명목 수령액이 매년 증가함
        current_pension_nom = int(pension_m * (1 + _INFLATION_RATE) ** yr)

        monthly_nom = (
            fund_m
            + (annuity_m if ann_on else 0)
            + deposit_m
            + (irp_m if irp_on else 0)
            + (consulting_m if consulting_on else 0)
            + home_pension_m   # 종신형 — 만료 없음
            + current_pension_nom
        )
        monthly_real = int(monthly_nom / (1 + _INFLATION_RATE) ** yr)

        rem_ann = 0 if not ann_on else int(annuity_cap * (annuity_years - yr) / annuity_years)
        rem_irp = 0 if not irp_on  else int(irp_cap     * (irp_years     - yr) / irp_years)
        rem_cap = fund_cap + rem_ann + deposit_cap + rem_irp

        milestones[yr] = {
            "monthly_nominal":   monthly_nom,
            "monthly_real":      monthly_real,
            "remaining_capital": rem_cap,
        }

    notes = []
    if annuity_m > 0:
        drop = annuity_m
        notes.append(f"즉시연금 {annuity_years}년 후 만료 → 월 {drop:,}원 감소")
    if irp_m > 0:
        notes.append(f"IRP {irp_years}년 후 만료 → 월 {irp_m:,}원 감소")
    if consulting_m > 0:
        notes.append(f"자녀 경영 자문료 {consulting_years}년 후 만료 → 월 {consulting_m:,}원 감소")
    if home_pension_m > 0:
        notes.append(f"주택연금 {home_pension_m:,}원: 종신 지급 (만료 없음)")
    notes.append("월배당펀드·예금 원금: 인출 없이 유지")

    return {"milestones": milestones, "notes": notes}


# risk_profile별 자산 배분 비율
_ALLOC_RATIO = {
    "conservative": {"fund": 0.20, "annuity": 0.33, "deposit": 0.33, "irp": 0.14},
    "balanced":     {"fund": 0.30, "annuity": 0.28, "deposit": 0.27, "irp": 0.15},
    "growth":       {"fund": 0.45, "annuity": 0.20, "deposit": 0.20, "irp": 0.15},
}

# risk_profile별 몬테카를로 가정 (연평균 수익률, 연 변동성)
_MC_PARAMS = {
    "conservative": (0.030, 0.015),   # 초안정 예금 위주
    "balanced":     (0.038, 0.040),   # 혼합형
    "growth":       (0.045, 0.060),   # 분산 투자형
}


def build_portfolio(total_capital: int, pension_monthly: int,
                     consulting_monthly: int = 0, annuity_years: int = 10,
                     age: int = 62, target_monthly: int = 3_000_000,
                     home_pension_monthly: int = 0,
                     risk_profile: str = "balanced") -> dict:
    alloc  = {}
    income = {}
    irp_drawdown_years = max(10, _LONGEVITY_AGE - age)
    ratio  = _ALLOC_RATIO.get(risk_profile, _ALLOC_RATIO["balanced"])

    if total_capital >= 100_000_000:
        p_fund    = _best("월배당")
        p_annuity = _best("즉시연금")
        p_deposit = _best("정기예금")
        p_irp     = _best("퇴직연금")

        fund_amt    = int(total_capital * ratio["fund"])
        annuity_amt = int(total_capital * ratio["annuity"])
        deposit_amt = int(total_capital * ratio["deposit"])
        irp_amt     = int(total_capital * ratio["irp"])

        alloc[f"{p_fund.get('name','월배당펀드')} ({p_fund.get('bank','JB자산운용')})"]  = fund_amt
        alloc[f"{p_annuity.get('name','즉시연금')} ({p_annuity.get('bank','JB생명')})"]  = annuity_amt
        alloc[f"{p_deposit.get('name','정기예금')} ({p_deposit.get('bank','전북은행')})"] = deposit_amt
        alloc[f"{p_irp.get('name','IRP')} ({p_irp.get('bank','전북은행')})"]              = irp_amt

        # 즉시연금: 사업비 7% 차감 후 실수령 원금으로 PMT 계산
        annuity_net = int(annuity_amt * (1 - _ANNUITY_EXPENSE_RATIO))
        # IRP: 원금 균등 분할 수령 (PMT, 기대여명까지)
        irp_monthly = _annuity_pmt(irp_amt, _rate(p_irp), irp_drawdown_years)

        # 세금 차감 후(세후) 실제 월 수령액 계산
        # 예금/배당펀드: 이자배당소득세 15.4%
        fund_monthly = int((fund_amt * _rate(p_fund) / 12) * (1 - 0.154))
        deposit_monthly = int((deposit_amt * _rate(p_deposit) / 12) * (1 - 0.154))
        
        # 즉시연금/IRP: 연금소득세 평균 약 5.5% 가정
        annuity_monthly = int(_annuity_pmt(annuity_net, _rate(p_annuity), annuity_years) * (1 - 0.055))
        irp_monthly = int(_annuity_pmt(irp_amt, _rate(p_irp), irp_drawdown_years) * (1 - 0.055))

        income[f"월배당 펀드 ({_rate(p_fund)*100:.1f}%, 세후)"]                              = fund_monthly
        income[f"즉시연금 ({_rate(p_annuity)*100:.2f}%, {annuity_years}년, 세후)"] = annuity_monthly
        income[f"예금이자 ({_rate(p_deposit)*100:.2f}%, 세후)"]                               = deposit_monthly
        income[f"IRP 연금수령 ({_rate(p_irp)*100:.2f}%, {irp_drawdown_years}년, 세후)"]      = irp_monthly

        rationale = (
            f"운용자산 {total_capital:,}원을 4개 상품에 분산합니다.\n"
            f"모든 수령액은 세후(이자/배당 15.4%, 연금 5.5% 차감) 기준입니다.\n"
            f"월배당펀드(35%): 매월 현금 수령으로 생활비 기반 확보\n"
            f"즉시연금(25%): 사업비 7% 차감 후 실수령 원금 {annuity_net:,}원 기준 {annuity_years}년 수령\n"
            f"정기예금(25%): 예금자보호 1억 한도 내 원금 보호\n"
            f"IRP(15%): {age}세 기준 {irp_drawdown_years}년 원금분할 수령 + 세액공제 혜택"
        )

    elif total_capital > 0:
        p_annuity   = _best("즉시연금")
        annuity_net = int(total_capital * (1 - _ANNUITY_EXPENSE_RATIO))
        alloc[f"{p_annuity.get('name','즉시연금')} ({p_annuity.get('bank','')})"] = total_capital
        annuity_monthly = int(_annuity_pmt(annuity_net, _rate(p_annuity), annuity_years) * (1 - 0.055))
        income[f"즉시연금 ({_rate(p_annuity)*100:.2f}%, {annuity_years}년, 세후)"] = annuity_monthly

        rationale = (
            f"운용가능 자산 {total_capital:,}원이 1억 미만이므로 즉시연금 단일 상품에 집중합니다.\n"
            f"세후(연금소득세 5.5% 차감) 및 사업비 차감 후 실수령 원금 {annuity_net:,}원 기준 {annuity_years}년 수령.\n"
            f"국민연금이 사실상 주 수입원이 됩니다."
        )
    else:
        rationale = "운용가능 자산이 없습니다. 국민연금이 유일한 수입원입니다."

    if consulting_monthly > 0:
        income["자문료·급여"] = consulting_monthly
        rationale += f"\n가업 승계 조건으로 자녀에게서 매월 {consulting_monthly:,}원의 자문료를 10년간 수령하여 기초 생활비를 보강합니다."

    if home_pension_monthly > 0:
        income["주택연금 (종신)"] = home_pension_monthly

    income["국민연금"] = pension_monthly
    income["합계"]    = sum(income.values())

    projection = _long_term_projection(
        {"monthly_income": income, "allocation": alloc},
        annuity_years=annuity_years,
        irp_years=irp_drawdown_years,
        consulting_years=10,
    )

    # 몬테카를로 생존 확률 (100세까지) — 목표 생활비에서 연금·자문료 수입을
    # 뺀 순인출 기준, CPP 의료비 쇼크 포함 (tools/monte_carlo.py)
    mc_months = max((100 - age) * 12, 12)
    mc_mean, mc_std = _MC_PARAMS.get(risk_profile, _MC_PARAMS["balanced"])
    monte_carlo = run_retirement_mc(
        total_capital, mc_mean, mc_std,
        build_withdrawal_schedule(
            target_monthly, pension_monthly, home_pension_monthly,
            consulting_monthly, months=mc_months,
        ),
        start_age=age, months=mc_months,
    ) if total_capital > 0 else {}

    return {
        "total_capital":        total_capital,
        "allocation":           alloc,
        "monthly_income":       income,
        "portfolio_rationale":  rationale,
        "target_monthly":       target_monthly,
        "surplus_monthly":      income["합계"] - target_monthly,
        "long_term_projection": projection,
        "monte_carlo":          monte_carlo,
        "risk_note": "펀드·연금 상품은 원금 손실 가능성이 있습니다. 가입 전 위험등급을 반드시 확인하세요.",
    }


def post_exit_wm_agent(state: AgentState) -> dict:
    if "PostExitWM" not in state.get("selected_agents", []):
        return {}

    profile        = state.get("user_profile", {})
    personal       = profile.get("personal_assets", {})
    biz            = profile.get("business", {})
    age            = profile.get("age", 62)
    pension        = personal.get("pension_monthly_expected", 900_000)
    savings        = personal.get("savings", 0)
    monthly_profit    = biz.get("monthly_profit", 4_500_000)
    years_operating   = biz.get("years_operating", 10)
    annual_income     = monthly_profit * 12

    # 병렬 실행이므로 business_valuation 결과 대신 직접 계산
    valuation  = estimate_business_value(monthly_profit, years_operating)
    goodwill   = valuation["goodwill_estimate"]
    biz_val    = goodwill + biz.get("deposit", 0) + biz.get("equipment_value", 0)
    sale_tax   = calc_goodwill_tax(goodwill, other_income=annual_income).get("total_tax", 0)

    life = profile.get("life_factors", {})
    succession_ok  = life.get("succession", "예") == "예"
    target_monthly = life.get("target_monthly", 3_000_000)

    # 주택연금: 사용자가 활용 선택 시 계산 (모든 시나리오 공통 — 주택 귀속과 무관)
    home_value  = personal.get("real_estate", 0)
    use_home_pension = life.get("home_pension", "아니오") == "예"
    home_pension_m = home_pension_monthly(home_value, age) if use_home_pension and home_value > 0 else 0

    market_trend        = life.get("market_trend", "보합")
    retirement_timeline = life.get("retirement_timeline", "3년 이내")

    # ── 시나리오 A: 완전 매각 ─────────────────────────────────────
    # 사업 소득 없으므로 안정 위주. 상권 하락·은퇴 임박이면 더 보수적
    risk_a = "conservative" if (market_trend == "하락" or retirement_timeline == "1년 이내") else "balanced"
    capital_sale = max(biz_val - sale_tax, 0) + savings
    portfolio_sale = build_portfolio(capital_sale, pension, age=age,
                                      target_monthly=target_monthly,
                                      home_pension_monthly=home_pension_m,
                                      risk_profile=risk_a)

    # ── 시나리오 B/C: 자녀의 승계 의향이 없으면 생략 ───────────────
    portfolio_succession = None
    portfolio_hybrid     = None

    # 가업 지속 가치 (B·C 공통 기반)
    continuity_full = calc_business_continuity(
        monthly_profit, years_operating,
        market_trend=market_trend, consulting_rate=0.20,
    ) if succession_ok else None
    continuity_half = calc_business_continuity(
        monthly_profit, years_operating,
        market_trend=market_trend, consulting_rate=0.10,
    ) if succession_ok else None

    if succession_ok:
        # 시나리오 B: 완전 가업승계 — 사장님 수중에 현금 없음, 자문료 보완으로 성장 배분
        risk_b = "growth" if market_trend == "성장" else "balanced"
        consulting_fee_b = int(monthly_profit * 0.2)
        capital_succession   = savings
        portfolio_succession = build_portfolio(capital_succession, pension,
                                                consulting_monthly=consulting_fee_b, age=age,
                                                target_monthly=target_monthly,
                                                home_pension_monthly=home_pension_m,
                                                risk_profile=risk_b)
        portfolio_succession["business_continuity"] = continuity_full

        # 시나리오 C: 절충 — 권리금 50% 현금화, 나머지 + 보증금 + 설비는 자녀에게 승계
        consulting_fee_c = int(monthly_profit * 0.1)
        half_goodwill    = goodwill // 2
        partial_tax      = calc_goodwill_tax(half_goodwill, other_income=annual_income).get("total_tax", 0)
        capital_hybrid   = half_goodwill - partial_tax + savings
        portfolio_hybrid = build_portfolio(capital_hybrid, pension,
                                            consulting_monthly=consulting_fee_c, age=age,
                                            target_monthly=target_monthly,
                                            home_pension_monthly=home_pension_m,
                                            risk_profile="balanced")
        # C안: 자녀가 절반만 승계하므로 누적수익·재매각가치 50% 반영
        if continuity_half:
            portfolio_hybrid["business_continuity"] = {
                **continuity_half,
                "daughter_cumulative_income": continuity_half["daughter_cumulative_income"] // 2,
                "future_goodwill":            continuity_half["future_goodwill"] // 2,
                "family_asset_gain":          (continuity_half["daughter_cumulative_income"] // 2
                                               + continuity_half["future_goodwill"] // 2),
            }

    # ── CPP 의료비 쇼크 몬테카를로 — 시나리오 간 동일 난수(CRN) 통제 비교 ──
    # 수익률/변동성 가정: A 분산 포트폴리오 4.5%/6.0%, B 초안정 예금 3.0%/1.5%,
    # C 혼합형 3.8%/4.0% (발표 모형 sim.py와 정렬)
    mc_months = max((100 - age) * 12, 12)
    mc_specs = {
        "A": {
            "k0": capital_sale, "annual_mean": 0.045, "annual_std": 0.060,
            "withdrawals": build_withdrawal_schedule(
                target_monthly, pension, home_pension_m, 0, months=mc_months),
        },
    }
    if portfolio_succession:
        mc_specs["B"] = {
            "k0": capital_succession, "annual_mean": 0.030, "annual_std": 0.015,
            "withdrawals": build_withdrawal_schedule(
                target_monthly, pension, home_pension_m, consulting_fee_b, months=mc_months),
        }
    if portfolio_hybrid:
        mc_specs["C"] = {
            "k0": capital_hybrid, "annual_mean": 0.038, "annual_std": 0.040,
            "withdrawals": build_withdrawal_schedule(
                target_monthly, pension, home_pension_m, consulting_fee_c, months=mc_months),
        }
    mc_comparison = run_scenario_comparison(mc_specs, start_age=age, months=mc_months)
    # 각 포트폴리오의 생존확률을 통제 비교 결과로 교체 (동일 난수 기준)
    if mc_comparison.get("A"):
        portfolio_sale["monte_carlo"] = mc_comparison["A"]
    if portfolio_succession and mc_comparison.get("B"):
        portfolio_succession["monte_carlo"] = mc_comparison["B"]
    if portfolio_hybrid and mc_comparison.get("C"):
        portfolio_hybrid["monte_carlo"] = mc_comparison["C"]

    scenario_b_text = ""
    scenario_c_text = ""
    if portfolio_succession and continuity_full:
        c = continuity_full
        scenario_b_text = (
            f"시나리오 B (완전 승계)\n"
            f"  사장님 월 수령: {portfolio_succession['monthly_income']['합계']:,}원 "
            f"(목표 대비 {portfolio_succession['surplus_monthly']:+,}원)\n"
            f"  [가업 지속 가치 — 상권 트렌드: {c['market_trend']}, 연 {c['annual_growth_rate']*100:+.0f}%]\n"
            f"  자녀 10년 누적 수익: {c['daughter_cumulative_income']:,}원\n"
            f"  10년 후 권리금 추정: {c['future_goodwill']:,}원 ({c['future_grade']})\n"
            f"  가족 총자산 증가: {c['family_asset_gain']:,}원\n\n"
        )
    if portfolio_hybrid:
        bc = portfolio_hybrid.get("business_continuity", {})
        scenario_c_text = (
            f"시나리오 C (절충: 권리금 절반 매각 + 절반 승계)\n"
            f"  사장님 월 수령: {portfolio_hybrid['monthly_income']['합계']:,}원 "
            f"(목표 대비 {portfolio_hybrid['surplus_monthly']:+,}원)\n"
            + (
                f"  [가업 지속 가치 — 절반 승계 기준]\n"
                f"  자녀 10년 누적 수익: {bc['daughter_cumulative_income']:,}원\n"
                f"  10년 후 권리금 추정: {bc['future_goodwill']:,}원\n"
                f"  가족 총자산 증가: {bc['family_asset_gain']:,}원\n\n"
                if bc else "\n"
            )
        )

    llm = get_llm("smart", temperature=0.1)
    advice = llm.invoke([
        SystemMessage(content=(
            "JB금융그룹 은퇴 전문 PB입니다.\n"
            "마크다운 기호(*, **, #, `)를 절대 사용하지 마세요. 번호와 줄바꿈만 쓰세요.\n"
            "제시된 시나리오의 노후 현금흐름을 사장님 본인 관점에서 비교하고, "
            "각 선택의 장단점을 숫자 근거와 함께 명확히 제시하세요."
        )),
        HumanMessage(content=(
            f"고객: {age}세 / 개인 저축 {savings:,}원 / 국민연금 월 {pension:,}원\n\n"
            f"시나리오 A (완전 매각)\n"
            f"  세금 {sale_tax:,}원 차감 후 운용자산: {capital_sale:,}원\n"
            f"  사장님 월 수령: {portfolio_sale['monthly_income']['합계']:,}원 "
            f"(목표 대비 {portfolio_sale['surplus_monthly']:+,}원)\n\n"
            f"{scenario_b_text}"
            f"{scenario_c_text}"
            f"질문: {state['query']}\n\n"
            "시나리오를 비교하고 사장님 상황에 가장 적합한 선택을 제안해주세요."
        )),
    ]).content

    combined = {
        **portfolio_sale,
        "scenario_sale":       portfolio_sale,
        "scenario_succession": portfolio_succession,
        "scenario_hybrid":     portfolio_hybrid,
        "monte_carlo_comparison": mc_comparison,
        "advice": advice,
    }

    return {"retirement_portfolio": combined, "active_agents": ["PostExitWM"]}
