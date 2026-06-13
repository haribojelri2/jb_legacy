"""tools/calculators.py 골든값 단위 테스트.

OVERVIEW.md의 데모 기준 수치(이사장 페르소나)를 고정해
계산 로직 변경 시 데모 수치가 깨지는 것을 즉시 감지한다.
서버·API 키 불필요: python -m pytest tests/test_calculators.py -v
"""

from tools.calculators import (
    calc_business_continuity,
    calc_gift_tax_general,
    calc_gift_tax_special,
    calc_goodwill_tax,
    calc_income_tax,
    design_retirement_cashflow,
    estimate_business_value,
    get_tax_bracket,
    _INCOME_TAX_BRACKETS,
)


# ── 권리금 산정 (수익환원법) ──────────────────────────────────

def test_estimate_business_value_lee_sajang():
    """이사장: 월순이익 450만 × 36개월(20년 이상) = 권리금 1억6,200만."""
    r = estimate_business_value(4_500_000, 30)
    assert r["multiple"] == 36
    assert r["grade"] == "A (우량)"
    assert r["goodwill_estimate"] == 162_000_000


def test_estimate_business_value_multiple_boundaries():
    assert estimate_business_value(1_000_000, 9)["multiple"] == 24    # 신생
    assert estimate_business_value(1_000_000, 10)["multiple"] == 30   # 안정
    assert estimate_business_value(1_000_000, 19)["multiple"] == 30
    assert estimate_business_value(1_000_000, 20)["multiple"] == 36   # 우량


# ── 종합소득세 누진 구간 ─────────────────────────────────────

def test_income_tax_bracket_boundaries():
    """각 구간 상한에서의 세액 (국세청 2025 공식)."""
    cases = [
        (14_000_000,    840_000),    # 6%
        (50_000_000,  6_240_000),    # 15% - 126만
        (88_000_000, 15_360_000),    # 24% - 576만
        (150_000_000, 37_060_000),   # 35% - 1,544만
        (300_000_000, 94_060_000),   # 38% - 1,994만
        (500_000_000, 174_060_000),  # 40% - 2,594만
        (1_000_000_000, 384_060_000),  # 42% - 3,594만
    ]
    for taxable, expected_national in cases:
        r = calc_income_tax(taxable)
        assert r["national_tax"] == expected_national, f"taxable={taxable:,}"
        assert r["local_tax"] == int(expected_national * 0.1)


def test_income_tax_continuity_at_boundaries():
    """구간 경계에서 세액이 불연속으로 튀지 않아야 함 (누진공제 검증)."""
    for limit, _, _ in _INCOME_TAX_BRACKETS[:-1]:
        below = calc_income_tax(int(limit))["national_tax"]
        above = calc_income_tax(int(limit) + 1)["national_tax"]
        assert abs(above - below) <= 1, f"불연속 @ {limit:,}: {below:,} vs {above:,}"


def test_get_tax_bracket_matches_calc():
    """표시용 구간 조회가 실제 계산과 동일 구간을 반환 (세율표 단일화 검증)."""
    for taxable in [10_000_000, 60_000_000, 118_800_000, 200_000_000,
                    350_000_000, 700_000_000, 2_000_000_000]:
        rate, deduction = get_tax_bracket(taxable)
        r = calc_income_tax(taxable)
        assert rate == r["rate"], f"taxable={taxable:,}"
        assert r["national_tax"] == max(0, int(taxable * rate - deduction))


def test_get_tax_bracket_over_300m_is_40_percent():
    """회귀 방지: 3~5억 구간은 45%가 아니라 40% (synthesizer 표시 버그)."""
    assert get_tax_bracket(350_000_000) == (0.40, 25_940_000)
    assert get_tax_bracket(700_000_000) == (0.42, 35_940_000)


# ── 권리금 기타소득세 (이사장 데모 수치) ─────────────────────

def test_goodwill_tax_lee_sajang():
    """권리금 1.62억 + 사업소득 5,400만 → 세금 2,875만 (OVERVIEW 기준)."""
    r = calc_goodwill_tax(162_000_000, other_income=54_000_000)
    assert r["goodwill_taxable_portion"] == 64_800_000   # 1.62억 × 40%
    assert r["rate"] == 0.35                              # 합산 1.188억 → 35% 구간
    assert r["national_tax"] == 26_140_000
    assert r["local_tax"] == 2_614_000
    assert r["total_tax"] == 28_754_000


# ── 가업승계 과세특례 (조특법 30조의6) ───────────────────────

def test_gift_tax_special_lee_sajang():
    """사업가치 3.12억 < 10억 공제 → 증여세 0원."""
    r = calc_gift_tax_special(312_000_000)
    assert r["taxable"] == 0
    assert r["total_tax"] == 0


def test_gift_tax_special_boundaries():
    assert calc_gift_tax_special(1_000_000_000)["total_tax"] == 0     # 정확히 10억
    r = calc_gift_tax_special(1_100_000_000)                          # 10억 초과 1억
    assert r["taxable"] == 100_000_000
    assert r["gift_tax"] == 10_000_000                                # 10%
    assert r["total_tax"] == 11_000_000                               # 지방세 포함
    r60 = calc_gift_tax_special(8_000_000_000)                        # 60억 초과분 20%
    assert r60["gift_tax"] == int(6_000_000_000 * 0.10 + 1_000_000_000 * 0.20)


def test_gift_tax_general():
    """일반 증여: 3.12억 − 5천만 공제 = 2.62억 → 20% 구간."""
    r = calc_gift_tax_general(312_000_000)
    assert r["taxable"] == 262_000_000
    assert r["gift_tax"] == 42_400_000      # 2.62억 × 20% − 1,000만
    assert r["total_tax"] == 46_640_000     # 지방세 포함


# ── 가업 지속 가치 (3축 프레이밍의 B/C안 근거) ───────────────

def test_business_continuity_stable_market():
    """이사장 B안, 상권 보합: 가족 총자산 증가 ~6.35억 (OVERVIEW 기준)."""
    c = calc_business_continuity(4_500_000, 30, "보합", 0.20)
    assert c["annual_growth_rate"] == 0.01
    assert c["daughter_cumulative_income"] == 456_487_254
    assert c["future_goodwill"] == 178_948_784
    assert c["family_asset_gain"] == 635_436_038
    assert c["future_multiple"] == 36
    assert c["current_grade"] == "A(우량)"


def test_business_continuity_market_trend_mapping():
    grow = calc_business_continuity(4_500_000, 30, "성장", 0.20)
    drop = calc_business_continuity(4_500_000, 30, "하락", 0.20)
    assert grow["annual_growth_rate"] == 0.05
    assert drop["annual_growth_rate"] == -0.03
    assert grow["family_asset_gain"] == 834_414_131
    assert drop["family_asset_gain"] == 486_228_683
    # 성장 > 보합 > 하락 순서 보존
    stable = calc_business_continuity(4_500_000, 30, "보합", 0.20)
    assert grow["family_asset_gain"] > stable["family_asset_gain"] > drop["family_asset_gain"]


def test_business_continuity_consulting_rate_reduces_income():
    high = calc_business_continuity(4_500_000, 30, "보합", consulting_rate=0.10)
    low = calc_business_continuity(4_500_000, 30, "보합", consulting_rate=0.30)
    assert high["daughter_cumulative_income"] > low["daughter_cumulative_income"]


# ── 은퇴 현금흐름 포트폴리오 ─────────────────────────────────

def test_design_retirement_cashflow_allocation():
    """배분 37.5/37.5/25%, 합계가 원금과 일치 (절사 오차 ≤ 2원)."""
    r = design_retirement_cashflow(330_000_000, 900_000, 3_000_000)
    assert abs(sum(r["allocation"].values()) - 330_000_000) <= 2
    assert r["monthly_income"]["합계"] == 2_005_155
    assert r["surplus_monthly"] == 2_005_155 - 3_000_000
    assert r["monthly_income"]["국민연금"] == 900_000
