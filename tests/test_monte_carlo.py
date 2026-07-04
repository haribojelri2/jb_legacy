"""tools/monte_carlo.py 특성 단위 테스트 (시드 고정 — 결정론)."""

import numpy as np

from tools.monte_carlo import (
    build_withdrawal_schedule,
    generate_market_randoms,
    run_retirement_mc,
    run_scenario_comparison,
    solve_target_monthly,
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
    """자문료는 120개월 동안만 정확히 차감 (물가 에스컬레이션과 독립)."""
    w = build_withdrawal_schedule(3_000_000, 900_000, 0, 900_000,
                                  consulting_months=120, months=_MONTHS)
    w_no = build_withdrawal_schedule(3_000_000, 900_000, 0, 0, months=_MONTHS)
    assert w[0] == 3_000_000 - 900_000 - 900_000
    assert np.allclose(w[:120], w_no[:120] - 900_000)
    assert np.allclose(w[120:], w_no[120:])


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


def test_inflation_reduces_survival():
    """물가상승 반영 시 인출 부담 증가 → 생존확률이 같거나 낮아야 함."""
    w_flat = build_withdrawal_schedule(2_500_000, 900_000, months=_MONTHS, inflation_rate=0.0)
    w_infl = build_withdrawal_schedule(2_500_000, 900_000, months=_MONTHS)  # 기본 연 2%
    flat = run_retirement_mc(350_000_000, 0.033, 0.012, w_flat, months=_MONTHS)
    infl = run_retirement_mc(350_000_000, 0.033, 0.012, w_infl, months=_MONTHS)
    assert infl["survival_probability"] <= flat["survival_probability"]


def test_goal_seek_meets_target_survival():
    """역산된 지속가능 생활비는 실제로 목표 생존확률을 달성해야 함."""
    gs = solve_target_monthly(300_000_000, 0.033, 0.012,
                              pension_monthly=900_000, months=_MONTHS,
                              target_survival=85.0)
    assert gs["achievable"]
    assert gs["sustainable_monthly"] > 0
    assert gs["survival_probability"] >= 85.0


def test_goal_seek_monotonic_in_capital():
    """운용자산이 클수록 지속가능 생활비가 같거나 높아야 함."""
    small = solve_target_monthly(100_000_000, 0.033, 0.012, months=_MONTHS)
    big = solve_target_monthly(500_000_000, 0.033, 0.012, months=_MONTHS)
    assert big["sustainable_monthly"] >= small["sustainable_monthly"]


def test_goal_seek_deterministic():
    """CRN 고정 시드 → 같은 입력은 항상 같은 역산 결과."""
    a = solve_target_monthly(300_000_000, 0.033, 0.012, months=_MONTHS)
    b = solve_target_monthly(300_000_000, 0.033, 0.012, months=_MONTHS)
    assert a == b
