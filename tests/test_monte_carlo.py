"""tools/monte_carlo.py 특성 단위 테스트 (시드 고정 — 결정론)."""

import numpy as np

from tools.monte_carlo import (
    build_withdrawal_schedule,
    generate_market_randoms,
    run_retirement_mc,
    run_scenario_comparison,
)

_MONTHS = (100 - 62) * 12


def _spec(k0, mean, std, w):
    return {"k0": k0, "annual_mean": mean, "annual_std": std, "withdrawals": w}


def test_reproducible_with_fixed_seed():
    w = build_withdrawal_schedule(3_000_000, 900_000, months=_MONTHS)
    r1 = run_retirement_mc(300_000_000, 0.045, 0.06, w, months=_MONTHS)
    r2 = run_retirement_mc(300_000_000, 0.045, 0.06, w, months=_MONTHS)
    assert r1 == r2


def test_zero_capital_returns_empty():
    w = build_withdrawal_schedule(3_000_000, months=_MONTHS)
    assert run_retirement_mc(0, 0.045, 0.06, w, months=_MONTHS) == {}


def test_survival_curve_monotone_decreasing():
    w = build_withdrawal_schedule(3_000_000, 900_000, months=_MONTHS)
    r = run_retirement_mc(300_000_000, 0.045, 0.06, w, months=_MONTHS)
    probs = list(r["survival_curve"].values())
    assert all(a >= b for a, b in zip(probs, probs[1:]))
    assert r["survival_probability"] == probs[-1]


def test_more_capital_never_hurts():
    w = build_withdrawal_schedule(3_000_000, 900_000, months=_MONTHS)
    lo = run_retirement_mc(200_000_000, 0.045, 0.06, w, months=_MONTHS)
    hi = run_retirement_mc(500_000_000, 0.045, 0.06, w, months=_MONTHS)
    assert hi["survival_probability"] >= lo["survival_probability"]


def test_net_accumulation_survives():
    """순적립(인출 음수)이면 의료비 쇼크에도 사실상 전 구간 생존."""
    w = build_withdrawal_schedule(1_000_000, 900_000, 600_000, 900_000,
                                  consulting_months=_MONTHS, months=_MONTHS)
    assert (w < 0).all()
    r = run_retirement_mc(500_000_000, 0.038, 0.04, w, months=_MONTHS)
    assert r["survival_probability"] >= 99.0


def test_consulting_expiry_in_schedule():
    w = build_withdrawal_schedule(3_000_000, 900_000, 0, 900_000,
                                  consulting_months=120, months=_MONTHS)
    assert w[0] == 3_000_000 - 900_000 - 900_000
    assert w[119] == w[0]
    assert w[120] == 3_000_000 - 900_000


def test_ruin_brackets_sum_with_survival():
    """고갈 구간 합계 + 최종 생존확률 ≈ 100%."""
    w = build_withdrawal_schedule(3_000_000, 900_000, months=_MONTHS)
    r = run_retirement_mc(300_000_000, 0.045, 0.06, w, months=_MONTHS)
    total = sum(r["ruin_age_brackets"].values()) + r["survival_probability"]
    assert abs(total - 100.0) < 0.5


def test_comparison_uses_common_random_numbers():
    """동일 스펙 시나리오 2개는 CRN으로 완전히 동일한 결과여야 함."""
    w = build_withdrawal_schedule(3_000_000, 900_000, months=_MONTHS)
    out = run_scenario_comparison(
        {"X": _spec(300_000_000, 0.045, 0.06, w),
         "Y": _spec(300_000_000, 0.045, 0.06, w)},
        months=_MONTHS,
    )
    assert out["X"] == out["Y"]
    assert out["_model"]["sims"] == 1000


def test_medical_shock_reduces_survival():
    """의료비 쇼크가 없으면(λ=0) 생존확률이 같거나 높아야 함."""
    w = build_withdrawal_schedule(2_500_000, 900_000, 565_000, months=_MONTHS)
    base = run_retirement_mc(350_000_000, 0.045, 0.06, w, months=_MONTHS)
    no_shock = run_retirement_mc(350_000_000, 0.045, 0.06, w, months=_MONTHS,
                                 lam_annual=0.0)
    assert no_shock["survival_probability"] >= base["survival_probability"]
