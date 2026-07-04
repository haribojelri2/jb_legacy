"""은퇴 자산 생존 확률 몬테카를로 시뮬레이션 — CPP 의료비 쇼크 포함.

모형 (확률통계 발표자료 '은퇴자산 생존확률 시뮬레이션'과 동일):
  - 자산 수익률: 기하 브라운 운동 근사 (월 수익률 ~ N(월평균, 월변동성))
  - 긴급 의료비: 복합 포아송 과정(CPP) — 발생 횟수 Poisson(연 0.25회),
    1회 지출액 지수분포(평균 3,000만원)
  - 시나리오 간 동일 난수(CRN) 공유 → 동일 시장 국면·쇼크 타이밍으로 통제 비교
  - 시드 고정(42) → 데모 재현성 보장

월 자산 갱신식:
  K_{t+1} = K_t × (1 + r_t) − W_t − S_t
  (W_t: 순인출액 = 목표 생활비 − 연금·자문료 수입, 음수면 순적립 / S_t: 의료비 쇼크)
"""

import numpy as np

_MAX_SHOCKS_PER_MONTH = 5   # 월 최대 의료비 지출 발생 횟수 가정

DEFAULT_LAM_ANNUAL = 0.25          # 의료비 쇼크 연평균 발생 횟수 (4년에 1회 꼴)
DEFAULT_AVG_SHOCK  = 30_000_000    # 1회 평균 지출액 (지수분포)
DEFAULT_SIMS       = 1_000
DEFAULT_SEED       = 42


def generate_market_randoms(
    months: int,
    sims: int = DEFAULT_SIMS,
    lam_annual: float = DEFAULT_LAM_ANNUAL,
    avg_shock: int = DEFAULT_AVG_SHOCK,
    seed: int = DEFAULT_SEED,
) -> tuple[np.ndarray, np.ndarray]:
    """시나리오 간 공유할 공통 난수 생성 (CRN).

    반환: (z 표준정규 난수 (sims, months), 월별 의료비 쇼크 합계 (sims, months))
    """
    rng = np.random.default_rng(seed)
    z = rng.normal(0.0, 1.0, (sims, months))
    counts = rng.poisson(lam_annual / 12, (sims, months))
    costs = rng.exponential(avg_shock, (sims, months, _MAX_SHOCKS_PER_MONTH))
    mask = np.arange(_MAX_SHOCKS_PER_MONTH)[None, None, :] < counts[:, :, None]
    shocks = (costs * mask).sum(axis=2)
    return z, shocks


def build_withdrawal_schedule(
    target_monthly: int,
    pension_monthly: int = 0,
    home_pension_monthly: int = 0,
    consulting_monthly: int = 0,
    consulting_months: int = 120,
    months: int = 456,
) -> np.ndarray:
    """월 순인출액 스케줄: 목표 생활비 − (국민연금 + 주택연금 + 자문료).

    자문료는 consulting_months(기본 10년) 동안만 수령. 음수면 순적립.
    """
    w = np.full(months, float(target_monthly - pension_monthly - home_pension_monthly))
    w[: min(consulting_months, months)] -= float(consulting_monthly)
    return w


def run_retirement_mc(
    k0: int,
    annual_mean: float,
    annual_std: float,
    withdrawals,
    *,
    start_age: int = 62,
    randoms: tuple[np.ndarray, np.ndarray] | None = None,
    months: int = 456,
    sims: int = DEFAULT_SIMS,
    lam_annual: float = DEFAULT_LAM_ANNUAL,
    avg_shock: int = DEFAULT_AVG_SHOCK,
    seed: int = DEFAULT_SEED,
) -> dict:
    """단일 시나리오 시뮬레이션.

    withdrawals: 길이 months의 월 순인출액 배열 (build_withdrawal_schedule 참고)
    randoms: generate_market_randoms() 결과. 시나리오 비교 시 동일 난수를 넘겨 통제.
    """
    if k0 <= 0:
        return {}

    if randoms is None:
        randoms = generate_market_randoms(months, sims, lam_annual, avg_shock, seed)
    z, shocks = randoms
    sims, months = z.shape

    w = np.asarray(withdrawals, dtype=float)
    if w.shape[0] < months:
        w = np.concatenate([w, np.full(months - w.shape[0], w[-1])])

    monthly_mean = (1 + annual_mean) ** (1 / 12) - 1
    monthly_std = annual_std / np.sqrt(12)

    cap = np.full(sims, float(k0))
    alive = np.ones(sims, dtype=bool)
    ruin_month = np.full(sims, -1, dtype=int)
    years = months // 12
    curve = np.zeros(years)

    for t in range(months):
        ret = monthly_mean + monthly_std * z[:, t]
        cap = np.where(alive, cap * (1 + ret) - w[t] - shocks[:, t], 0.0)
        ruined_now = alive & (cap <= 0)
        ruin_month[ruined_now] = t
        alive &= cap > 0
        cap = np.maximum(cap, 0.0)
        if (t + 1) % 12 == 0:
            curve[(t + 1) // 12 - 1] = alive.mean()

    final_caps = np.sort(cap)
    end_age = start_age + years

    # 자산 고갈 나이 분포 (연령 구간별 %)
    ruin_age = np.where(ruin_month >= 0, start_age + ruin_month // 12, -1)
    bracket_bounds = [(start_age, 70), (71, 80), (81, 90), (91, end_age)]
    ruin_age_brackets = {
        f"{lo}-{hi}세": round(float(((ruin_age >= lo) & (ruin_age <= hi)).sum()) / sims * 100, 1)
        for lo, hi in bracket_bounds
    }

    return {
        "survival_probability": round(float(alive.mean()) * 100, 1),
        "survival_curve": {start_age + y + 1: round(float(curve[y]) * 100, 1) for y in range(years)},
        "ruin_age_brackets": ruin_age_brackets,
        "median_final_capital": int(final_caps[sims // 2]),
        "p10_final_capital": int(final_caps[sims // 10]),
        "simulations": sims,
        "years": years,
        "target_age": end_age,
        "monthly_withdrawal": int(w[0]),
        "annual_mean": annual_mean,
        "annual_std": annual_std,
    }


def solve_target_monthly(
    k0: int,
    annual_mean: float,
    annual_std: float,
    *,
    pension_monthly: int = 0,
    home_pension_monthly: int = 0,
    consulting_monthly: int = 0,
    consulting_months: int = 120,
    months: int = 456,
    start_age: int = 62,
    target_survival: float = 85.0,
    hi: int = 20_000_000,
    tol: int = 10_000,
) -> dict:
    """목표 생존확률(%)을 달성하는 최대 지속가능 월 생활비 역산 (이분 탐색).

    CRN(시드 고정) 덕분에 같은 생활비는 항상 같은 생존확률을 내고,
    생활비가 낮을수록 생존확률은 단조 증가 → 탐색이 결정론적으로 수렴한다.
    반환: {sustainable_monthly, survival_probability, target_survival, achievable}
    """
    if k0 <= 0:
        return {}

    randoms = generate_market_randoms(months)  # 탐색 전체에서 동일 난수 공유

    def _survival(monthly: int) -> float:
        w = build_withdrawal_schedule(
            monthly, pension_monthly, home_pension_monthly,
            consulting_monthly, consulting_months, months,
        )
        res = run_retirement_mc(k0, annual_mean, annual_std, w,
                                start_age=start_age, randoms=randoms, months=months)
        return res["survival_probability"]

    lo = 0
    if _survival(hi) >= target_survival:
        lo = hi  # 상한에서도 달성 → 사실상 제약 없음
    elif _survival(lo) < target_survival:
        # 순적립 상태(생활비 0)여도 의료비 쇼크만으로 목표 미달 → 달성 불가
        return {
            "sustainable_monthly": 0,
            "survival_probability": _survival(lo),
            "target_survival": target_survival,
            "achievable": False,
        }
    else:
        while hi - lo > tol:
            mid = (lo + hi) // 2
            if _survival(mid) >= target_survival:
                lo = mid
            else:
                hi = mid

    return {
        "sustainable_monthly": int(lo),
        "survival_probability": _survival(lo),
        "target_survival": target_survival,
        "achievable": True,
    }


def run_scenario_comparison(
    scenarios: dict[str, dict],
    *,
    start_age: int = 62,
    months: int = 456,
    sims: int = DEFAULT_SIMS,
    lam_annual: float = DEFAULT_LAM_ANNUAL,
    avg_shock: int = DEFAULT_AVG_SHOCK,
    seed: int = DEFAULT_SEED,
) -> dict:
    """여러 시나리오를 동일 난수(CRN)로 통제 비교.

    scenarios: {라벨: {"k0", "annual_mean", "annual_std", "withdrawals"}}
    반환: {라벨: run_retirement_mc 결과, "_model": 모형 메타데이터}
    """
    randoms = generate_market_randoms(months, sims, lam_annual, avg_shock, seed)
    out = {}
    for label, spec in scenarios.items():
        out[label] = run_retirement_mc(
            spec["k0"], spec["annual_mean"], spec["annual_std"], spec["withdrawals"],
            start_age=start_age, randoms=randoms,
        )
    out["_model"] = {
        "name": "CPP 의료비 쇼크 몬테카를로",
        "description": (
            f"복합 포아송 과정(연평균 {lam_annual}회, 평균 {avg_shock:,}원 지수분포) "
            f"의료비 쇼크 반영, {sims:,}회 경로 × {months // 12}년, "
            f"시나리오 간 동일 난수 통제 비교(CRN), 시드 고정"
        ),
        "lam_annual": lam_annual,
        "avg_shock": avg_shock,
        "sims": sims,
        "months": months,
        "seed": seed,
    }
    return out
