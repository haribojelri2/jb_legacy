"""세금 계산 · 사업가치 평가 · 현금흐름 설계 도구 (국세청 공식 세율 기준).

세율표·공제·배수 등 금융 상수는 config/params.yaml에서 주입한다(단일 출처).
세법 개정 시 코드가 아니라 params.yaml만 수정하면 즉시 반영된다.
"""

from config.params import PARAMS, brackets as _brackets

# ── 종합소득세 누진 구간 (params.yaml: income_tax.brackets) ─────────────────
_INCOME_TAX_BRACKETS = _brackets(PARAMS["income_tax"]["brackets"])
_LOCAL_TAX_RATIO = PARAMS["local_tax_ratio"]
_GOODWILL_TAXABLE_RATIO = PARAMS["goodwill"]["taxable_ratio"]
_GOODWILL_MULT = PARAMS["goodwill"]["multiples"]
_SPECIAL = PARAMS["gift_tax_special"]
_GENERAL = PARAMS["gift_tax_general"]
_MARKET_GROWTH = PARAMS["market_growth"]


def _mult_for(years: int) -> int:
    """업력별 권리금 배수(개월) — params.yaml: goodwill.multiples."""
    if years < 10:
        return _GOODWILL_MULT["under_10y"]
    if years < 20:
        return _GOODWILL_MULT["under_20y"]
    return _GOODWILL_MULT["over_20y"]


def get_tax_bracket(taxable_income: int) -> tuple[float, int]:
    """과세표준이 속한 종합소득세 구간의 (세율, 누진공제액) 반환.

    표시용 세율표가 실제 계산과 어긋나지 않도록 단일 출처로 사용한다.
    """
    for limit, rate, deduction in _INCOME_TAX_BRACKETS:
        if taxable_income <= limit:
            return rate, deduction
    _last = _INCOME_TAX_BRACKETS[-1]
    return _last[1], _last[2]


def calc_income_tax(taxable_income: int) -> dict:
    """종합소득세 계산 (지방소득세 10% 포함)."""
    for limit, rate, deduction in _INCOME_TAX_BRACKETS:
        if taxable_income <= limit:
            national = taxable_income * rate - deduction
            local = national * _LOCAL_TAX_RATIO
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
    goodwill_taxable = int(goodwill * _GOODWILL_TAXABLE_RATIO)
    total_taxable = goodwill_taxable + other_income
    result = calc_income_tax(total_taxable)
    result["goodwill"] = goodwill
    result["goodwill_taxable_portion"] = goodwill_taxable
    result["other_income"] = other_income
    result["description"] = (
        f"권리금 {goodwill:,}원 × {_GOODWILL_TAXABLE_RATIO*100:.0f}% = 과세표준 {goodwill_taxable:,}원\n"
        f"기타소득 포함 총 과세표준: {total_taxable:,}원\n"
        f"산출세액(지방세 포함): {result['total_tax']:,}원"
    )
    return result


def calc_gift_tax_special(business_value: int) -> dict:
    """가업승계 증여세 과세특례 (조특법 30조의6).
    - 10억원 공제 후 10% (60억 초과분 20%)
    - 한도 600억
    """
    deduction = _SPECIAL["deduction"]
    thr = _SPECIAL["threshold_over"]
    taxable = max(0, business_value - deduction)

    if taxable <= 0:
        tax = 0
    elif taxable <= thr:
        tax = int(taxable * _SPECIAL["rate_base"])
    else:
        tax = int(thr * _SPECIAL["rate_base"] + (taxable - thr) * _SPECIAL["rate_over"])

    local = int(tax * _LOCAL_TAX_RATIO)
    return {
        "business_value": business_value,
        "deduction": min(deduction, business_value),
        "taxable": taxable,
        "gift_tax": tax,
        "local_tax": local,
        "total_tax": tax + local,
        "description": (
            f"사업체 가치 {business_value:,}원\n"
            f"{deduction // 100_000_000}억원 공제 후 과세표준: {taxable:,}원\n"
            f"세율 {_SPECIAL['rate_base']*100:.0f}% 적용 → 증여세: {tax + local:,}원"
        ),
    }


def calc_gift_tax_general(business_value: int) -> dict:
    """일반 증여세 (성인 자녀 기본공제 5,000만원, 10년 합산)."""
    # 증여세 세율 (상속세 및 증여세법) — params.yaml: gift_tax_general
    brackets = _brackets(_GENERAL["brackets"])
    child_deduction = _GENERAL["child_deduction"]
    taxable = max(0, business_value - child_deduction)

    tax = 0
    for limit, rate, deduction in brackets:
        if taxable <= limit:
            tax = int(taxable * rate - deduction)
            break

    local = int(tax * _LOCAL_TAX_RATIO)
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


def resolve_succession_tax(business_value: int, years_operating: int,
                           entity: str = "개인") -> dict:
    """승계 세금 시나리오 결정 — 가업 10년 요건 + 개인/법인 형태 반영.

    - 10년 미만: 특례 대상 아님 → 일반 증여세
    - 10년 이상 + 법인: 가업승계 과세특례 직접 적용
    - 10년 이상 + 개인: 특례는 법인 주식 대상 → '법인 전환 후 승계' 시 적용(우회 전략)

    반환 dict는 calc_gift_tax_* 결과에 eligible/entity/label/note(+direct_general_tax)를 추가.
    """
    special = calc_gift_tax_special(business_value)
    general = calc_gift_tax_general(business_value)
    min_years = _SPECIAL["min_years"]
    if years_operating < min_years:
        return {**general, "eligible": False, "entity": entity,
                "label": "가업승계 (일반 증여세)",
                "note": (f"가업 영위 {years_operating}년({min_years}년 미만)이라 가업승계 "
                         f"과세특례 대상이 아니어서 일반 증여세를 적용했습니다.")}
    if entity == "법인":
        return {**special, "eligible": True, "entity": "법인",
                "label": "가업승계 과세특례"}
    return {**special, "eligible": True, "entity": "개인",
            "label": "가업승계 특례 (법인 전환 후)",
            "direct_general_tax": general["total_tax"],
            "note": (f"개인사업자는 가업승계 과세특례(조특법 30조의6)를 직접 적용받을 수 "
                     f"없습니다. 지금 바로 승계하면 일반 증여세 {general['total_tax']:,}원이지만, "
                     f"법인 전환 후 주식을 승계하면 특례로 {special['total_tax']:,}원까지 절감할 수 "
                     f"있습니다(전환 비용·사후관리 5년 유지 요건 별도 검토).")}


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
    annual_growth = _MARKET_GROWTH.get(market_trend, _MARKET_GROWTH.get("보합", 0.01))

    # 자녀 누적 순수익 (자문료 차감 후)
    daughter_cumulative = 0
    for yr in range(1, projection_years + 1):
        annual = monthly_profit * (1 + annual_growth) ** yr * 12
        daughter_cumulative += int(annual * (1 - consulting_rate))

    # N년 후 사업체 재매각 추정가
    future_monthly = monthly_profit * (1 + annual_growth) ** projection_years
    future_years   = years_operating + projection_years
    future_multiple = _mult_for(future_years)
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
    multiple = _mult_for(years_operating)
    if years_operating < 10:
        grade = "C (신생)"
    elif years_operating < 20:
        grade = "B (안정)"
    else:
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


def resolve_business_value(profile: dict) -> dict:
    """권리금·총 사업체 가치 단일 산출 — 명시 감정가 우선, 없으면 수익환원법.

    tax_succession과 post_exit_wm은 병렬 실행되어 서로 결과를 공유할 수 없으므로
    두 에이전트가 이 함수를 공통 호출해 동일한 권리금·가치를 사용한다.
    """
    biz = profile.get("business", {})
    monthly_profit  = biz.get("monthly_profit", 4_500_000)
    years_operating = biz.get("years_operating", 30)
    explicit = biz.get("goodwill")
    if explicit:
        goodwill = explicit
        business_value = profile.get("total_business_value") or (
            goodwill + biz.get("deposit", 0) + biz.get("equipment_value", 0)
        )
    else:
        goodwill = estimate_business_value(monthly_profit, years_operating)["goodwill_estimate"]
        business_value = goodwill + biz.get("deposit", 0) + biz.get("equipment_value", 0)
    return {"goodwill": goodwill, "business_value": business_value}


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
