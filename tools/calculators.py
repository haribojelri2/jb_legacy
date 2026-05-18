"""세금 계산 · 사업가치 평가 · 현금흐름 설계 도구 (국세청 공식 세율 기준)."""

# ── 2025년 종합소득세 누진 구간 (국세청 공식) ─────────────────
_INCOME_TAX_BRACKETS = [
    (14_000_000,   0.06,          0),
    (50_000_000,   0.15,  1_260_000),
    (88_000_000,   0.24,  5_760_000),
    (150_000_000,  0.35, 15_440_000),
    (300_000_000,  0.38, 19_940_000),
    (500_000_000,  0.40, 25_940_000),
    (1_000_000_000,0.42, 35_940_000),
    (float("inf"), 0.45, 65_940_000),
]


def calc_income_tax(taxable_income: int) -> dict:
    """종합소득세 계산 (지방소득세 10% 포함)."""
    for limit, rate, deduction in _INCOME_TAX_BRACKETS:
        if taxable_income <= limit:
            national = taxable_income * rate - deduction
            local = national * 0.1
            return {
                "taxable_income": taxable_income,
                "rate": rate,
                "national_tax": max(0, int(national)),
                "local_tax": max(0, int(local)),
                "total_tax": max(0, int(national + local)),
            }
    return {}


def calc_goodwill_tax(goodwill: int, other_income: int = 0) -> dict:
    """권리금 기타소득세 계산.
    - 필요경비 60% 인정 → 과세표준 = 권리금 × 40%
    - 다른 소득과 합산 종합과세
    """
    goodwill_taxable = int(goodwill * 0.4)
    total_taxable = goodwill_taxable + other_income
    result = calc_income_tax(total_taxable)
    result["goodwill"] = goodwill
    result["goodwill_taxable_portion"] = goodwill_taxable
    result["other_income"] = other_income
    result["description"] = (
        f"권리금 {goodwill:,}원 × 40% = 과세표준 {goodwill_taxable:,}원\n"
        f"기타소득 포함 총 과세표준: {total_taxable:,}원\n"
        f"산출세액(지방세 포함): {result['total_tax']:,}원"
    )
    return result


def calc_gift_tax_special(business_value: int) -> dict:
    """가업승계 증여세 과세특례 (조특법 30조의6).
    - 10억원 공제 후 10% (60억 초과분 20%)
    - 한도 600억
    """
    deduction = 1_000_000_000  # 10억
    taxable = max(0, business_value - deduction)

    if taxable <= 0:
        tax = 0
    elif taxable <= 6_000_000_000:  # 60억
        tax = int(taxable * 0.10)
    else:
        tax = int(6_000_000_000 * 0.10 + (taxable - 6_000_000_000) * 0.20)

    local = int(tax * 0.1)
    return {
        "business_value": business_value,
        "deduction": min(deduction, business_value),
        "taxable": taxable,
        "gift_tax": tax,
        "local_tax": local,
        "total_tax": tax + local,
        "description": (
            f"사업체 가치 {business_value:,}원\n"
            f"10억원 공제 후 과세표준: {taxable:,}원\n"
            f"세율 10% 적용 → 증여세: {tax + local:,}원"
        ),
    }


def calc_gift_tax_general(business_value: int) -> dict:
    """일반 증여세 (성인 자녀 기본공제 5,000만원, 10년 합산)."""
    # 증여세 세율 (상속세 및 증여세법)
    brackets = [
        (100_000_000,  0.10,          0),
        (500_000_000,  0.20, 10_000_000),
        (1_000_000_000,0.30, 60_000_000),
        (3_000_000_000,0.40,160_000_000),
        (float("inf"), 0.50,460_000_000),
    ]
    child_deduction = 50_000_000  # 성인 자녀 공제 5천만
    taxable = max(0, business_value - child_deduction)

    tax = 0
    for limit, rate, deduction in brackets:
        if taxable <= limit:
            tax = int(taxable * rate - deduction)
            break

    local = int(tax * 0.1)
    return {
        "business_value": business_value,
        "deduction": child_deduction,
        "taxable": taxable,
        "gift_tax": tax,
        "local_tax": local,
        "total_tax": max(0, tax + local),
        "description": (
            f"사업체 가치 {business_value:,}원\n"
            f"기본공제 5천만원 후 과세표준: {taxable:,}원\n"
            f"일반 증여세(지방세 포함): {max(0, tax + local):,}원"
        ),
    }


def calc_business_continuity(
    monthly_profit: int,
    years_operating: int,
    market_trend: str = "보합",
    consulting_rate: float = 0.20,
    projection_years: int = 10,
) -> dict:
    """승계 후 가업 지속 가치 계산 (자녀 관점 + 가족 총자산).

    상권 트렌드별 성장률:
      성장 +5% / 보합 +1% / 하락 -3%
    """
    growth_map = {"성장": 0.05, "보합": 0.01, "하락": -0.03}
    annual_growth = growth_map.get(market_trend, 0.01)

    # 자녀 누적 순수익 (자문료 차감 후)
    daughter_cumulative = 0
    for yr in range(1, projection_years + 1):
        annual = monthly_profit * (1 + annual_growth) ** yr * 12
        daughter_cumulative += int(annual * (1 - consulting_rate))

    # N년 후 사업체 재매각 추정가
    future_monthly = monthly_profit * (1 + annual_growth) ** projection_years
    future_years   = years_operating + projection_years
    future_multiple = 36 if future_years >= 20 else (30 if future_years >= 10 else 24)
    future_goodwill = int(future_monthly * future_multiple)

    family_asset_gain = daughter_cumulative + future_goodwill

    grade = lambda y: "A(우량)" if y >= 20 else ("B(안정)" if y >= 10 else "C(신생)")

    return {
        "annual_growth_rate":        annual_growth,
        "market_trend":              market_trend,
        "projection_years":          projection_years,
        "daughter_cumulative_income": daughter_cumulative,
        "future_monthly_profit":     int(future_monthly),
        "future_goodwill":           future_goodwill,
        "future_multiple":           future_multiple,
        "family_asset_gain":         family_asset_gain,
        "current_grade":             grade(years_operating),
        "future_grade":              grade(future_years),
    }


def estimate_business_value(monthly_profit: int, years_operating: int) -> dict:
    """사업체 권리금·적정가치 산정.
    - 권리금 배수: 영업연수·안정성 반영
    - 10년 미만: 24개월치, 10~20년: 30개월치, 20년 이상: 36개월치
    """
    if years_operating < 10:
        multiple = 24
        grade = "C (신생)"
    elif years_operating < 20:
        multiple = 30
        grade = "B (안정)"
    else:
        multiple = 36
        grade = "A (우량)"

    goodwill = monthly_profit * multiple
    return {
        "monthly_profit": monthly_profit,
        "years_operating": years_operating,
        "multiple": multiple,
        "grade": grade,
        "goodwill_estimate": goodwill,
        "description": (
            f"월 순이익 {monthly_profit:,}원 × {multiple}개월 배수\n"
            f"적정 권리금 추정: {goodwill:,}원 (등급: {grade})"
        ),
    }


def design_retirement_cashflow(
    total_capital: int,
    pension_monthly: int,
    target_monthly: int,
    years: int = 30,
) -> dict:
    """은퇴 후 30년 현금흐름 포트폴리오 설계."""
    # 포트폴리오 배분
    dividend_fund = int(total_capital * 0.375)   # 37.5% → 월배당
    deposit      = int(total_capital * 0.375)   # 37.5% → 예금
    annuity      = int(total_capital * 0.25)    # 25% → 연금

    # 예상 월 수령액
    dividend_monthly = int(dividend_fund * 0.045 / 12)    # 연 4.5% 분배
    deposit_monthly  = int(deposit * 0.0355 / 12)         # 연 3.55% (JB 기준)
    annuity_monthly  = int(annuity * 0.04 / 12)           # 연 4% 환산

    total_monthly = dividend_monthly + deposit_monthly + annuity_monthly + pension_monthly

    return {
        "total_capital": total_capital,
        "allocation": {
            "월배당펀드(JB자산운용)": dividend_fund,
            "정기예금(전북은행)":     deposit,
            "개인연금":               annuity,
        },
        "monthly_income": {
            "월배당펀드":  dividend_monthly,
            "예금이자":    deposit_monthly,
            "개인연금":    annuity_monthly,
            "국민연금":    pension_monthly,
            "합계":        total_monthly,
        },
        "target_monthly": target_monthly,
        "surplus_monthly": total_monthly - target_monthly,
        "total_years": years,
        "description": (
            f"총 운용자산 {total_capital:,}원 → 월 수령 합계: {total_monthly:,}원\n"
            f"(목표 {target_monthly:,}원 대비 월 {total_monthly - target_monthly:+,}원)"
        ),
    }
