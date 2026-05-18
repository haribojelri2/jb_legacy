"""Dynamic Valuation Agent — 마이데이터 기반 권리금 동적 평가 & 엑시트 타이밍 (DEMO MOCK).

본선에서 JB카드 마이데이터 API + 소상공인 상권정보 공공데이터 API 연동 예정.
현재는 mock_mydata.py 시뮬레이션 데이터를 사용.
"""

from data.db import calc_revenue_trend
from data.mock_mydata import COMPETITION_INDEX, LOCATION_SCORE

# 업종별 기준 배수 (순이익 × 배수 = 권리금)
_BASE_MULTIPLES = {
    "lee_sajang":   36,   # 한정식: 3년치
    "kim_soojang":  24,   # 분식: 2년치
    "park_wonjang": 48,   # 강남 카페: 4년치 (입지 프리미엄)
    "choi_daepyo":  30,   # 한식뷔페: 2.5년치
}

_DEFAULT_MULTIPLE = 30


def _trend_multiplier(yoy_pct: float) -> float:
    """전년비 매출 증감에 따른 배수 보정 (±20% 한도)."""
    if yoy_pct > 0.10:
        return 1.20
    if yoy_pct > 0.05:
        return 1.10
    if yoy_pct > 0.00:
        return 1.03
    if yoy_pct > -0.05:
        return 0.95
    if yoy_pct > -0.10:
        return 0.85
    return 0.75


def _competition_multiplier(idx: float) -> float:
    """경쟁강도에 따른 배수 보정."""
    if idx >= 0.75:
        return 0.85
    if idx >= 0.55:
        return 0.93
    return 1.00


def _location_multiplier(score: int) -> float:
    """입지 점수에 따른 배수 보정."""
    if score >= 85:
        return 1.15
    if score >= 70:
        return 1.05
    if score >= 55:
        return 0.97
    return 0.88


def _exit_timing(yoy_pct: float, competition: float, score: int) -> dict:
    """최적 엑시트 시점 추천."""
    risk_points = 0
    if yoy_pct < -0.05:
        risk_points += 2
    elif yoy_pct < 0:
        risk_points += 1

    if competition >= 0.75:
        risk_points += 2
    elif competition >= 0.55:
        risk_points += 1

    if score < 55:
        risk_points += 2
    elif score < 70:
        risk_points += 1

    if risk_points >= 4:
        return {"recommendation": "즉시", "window_months": 6, "urgency": "경보",
                "reason": "매출 하락 + 경쟁 심화 + 입지 약화가 동시 진행 중입니다. 권리금이 더 낮아지기 전에 매각을 서두르세요."}
    if risk_points >= 2:
        return {"recommendation": "6~18개월 내", "window_months": 18, "urgency": "주의",
                "reason": "일부 지표가 악화 중입니다. 12~18개월 안에 조건을 준비하고 매각 시점을 잡는 것을 권장합니다."}
    return {"recommendation": "여유 있음 (24개월+)", "window_months": None, "urgency": "정상",
            "reason": "현재 사업 상태가 양호합니다. 서두르지 않아도 되지만, 피크 시점에 매각하면 가장 유리합니다."}


def calc_dynamic_goodwill(user_id: str, monthly_profit: int | None = None) -> dict:
    """마이데이터 기반 권리금 동적 계산."""
    trend       = calc_revenue_trend(user_id)
    competition = COMPETITION_INDEX.get(user_id, 0.5)
    location    = LOCATION_SCORE.get(user_id, 70)

    if not trend:
        return {}

    # 적용 순이익: 인자 우선, 없으면 최근 6개월 평균
    profit = monthly_profit if monthly_profit else trend["recent_6m_avg"]

    base_multiple    = _BASE_MULTIPLES.get(user_id, _DEFAULT_MULTIPLE)
    yoy              = trend["yoy_change_pct"] / 100
    t_mult           = _trend_multiplier(yoy)
    c_mult           = _competition_multiplier(competition)
    l_mult           = _location_multiplier(location)
    adjusted_mult    = round(base_multiple * t_mult * c_mult * l_mult, 1)

    static_goodwill  = profit * base_multiple           # 기존 단순 계산
    dynamic_goodwill = int(profit * adjusted_mult)      # 마이데이터 보정값

    delta_pct = (dynamic_goodwill - static_goodwill) / static_goodwill * 100 if static_goodwill else 0

    timing = _exit_timing(yoy, competition, location)

    return {
        "monthly_profit_applied": profit,
        "base_multiple":          base_multiple,
        "adjusted_multiple":      adjusted_mult,
        "multiplier_breakdown": {
            "매출추세 보정": round(t_mult, 2),
            "경쟁강도 보정": round(c_mult, 2),
            "입지점수 보정": round(l_mult, 2),
        },
        "static_goodwill":        static_goodwill,
        "dynamic_goodwill":       dynamic_goodwill,
        "delta_pct":              round(delta_pct, 1),
        "trend_direction":        trend["trend_direction"],
        "exit_timing":            timing,
        "data_source":            "DEMO MOCK — 본선 마이데이터 API 연동 예정",
    }
