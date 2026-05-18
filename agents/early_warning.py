"""Early Warning Agent — 폐업 조기경보 대시보드 (DEMO MOCK).

본선에서 JB카드 마이데이터 API 실시간 연동 예정.
현재는 mock_mydata.py의 시뮬레이션 데이터를 사용.
"""

from data.db import calc_revenue_trend
from data.mock_mydata import COMPETITION_INDEX, LOCATION_SCORE


_RISK_THRESHOLDS = {
    "yoy_decline_warn":   -0.05,   # 전년비 -5% → 주의
    "yoy_decline_alert":  -0.10,   # 전년비 -10% → 경보
    "volatility_warn":     0.06,
    "volatility_alert":    0.10,
    "competition_warn":    0.60,
    "competition_alert":   0.75,
    "location_warn":       65,
    "location_alert":      50,
}


def _score_factor(value, warn, alert, higher_is_bad=True) -> tuple[int, str]:
    """(점수 0~100, 등급) 반환. higher_is_bad=True면 값이 클수록 위험."""
    if higher_is_bad:
        if value >= alert:
            return 20, "경보"
        if value >= warn:
            return 55, "주의"
        return 90, "정상"
    else:
        if value <= alert:
            return 20, "경보"
        if value <= warn:
            return 55, "주의"
        return 90, "정상"


def calc_health_score(user_id: str, monthly_profit_override: int = 0) -> dict:
    """사업체 건강 점수 계산. 4개 지표를 가중 평균해 0~100 종합점수 산출."""
    trend = calc_revenue_trend(user_id)
    if not trend:
        return {}

    # 사용자가 Step1에서 월순이익을 직접 입력한 경우 → 절댓값 스케일링
    # 비율 변화(추세·변동성)는 그대로 유지되므로 건강 점수 로직에 영향 없음
    if monthly_profit_override and trend.get("recent_6m_avg"):
        db_avg = trend["recent_6m_avg"]
        scale  = monthly_profit_override / db_avg
        trend  = {
            **trend,
            "recent_6m_avg":  monthly_profit_override,
            "prev_6m_avg":    int(trend["prev_6m_avg"] * scale),
            "history_10k":    [round(v * scale / 10000) for v in trend["history_10k"]],
        }

    competition = COMPETITION_INDEX.get(user_id, 0.5)
    location    = LOCATION_SCORE.get(user_id, 70)
    yoy         = trend["yoy_change_pct"] / 100      # -0.xx ~ +0.xx
    volatility  = trend["volatility"]

    # 각 지표별 점수·등급
    s_revenue, g_revenue = _score_factor(
        yoy,
        _RISK_THRESHOLDS["yoy_decline_warn"],
        _RISK_THRESHOLDS["yoy_decline_alert"],
        higher_is_bad=False,      # 낮을수록(하락) 위험
    )
    s_volatility, g_volatility = _score_factor(
        volatility,
        _RISK_THRESHOLDS["volatility_warn"],
        _RISK_THRESHOLDS["volatility_alert"],
    )
    s_competition, g_competition = _score_factor(
        competition,
        _RISK_THRESHOLDS["competition_warn"],
        _RISK_THRESHOLDS["competition_alert"],
    )
    s_location, g_location = _score_factor(
        location,
        _RISK_THRESHOLDS["location_warn"],
        _RISK_THRESHOLDS["location_alert"],
        higher_is_bad=False,      # 낮을수록 위험
    )

    # 가중 평균: 매출 추세 40% / 변동성 20% / 경쟁강도 25% / 입지 15%
    total = (
        s_revenue    * 0.40
        + s_volatility  * 0.20
        + s_competition * 0.25
        + s_location    * 0.15
    )
    total = round(total)

    if total >= 75:
        overall = "정상"
    elif total >= 50:
        overall = "주의"
    else:
        overall = "경보"

    # 위험 요인 메시지
    warnings = []
    if g_revenue == "경보":
        warnings.append(f"매출이 전년 대비 {trend['yoy_change_pct']:.1f}% 감소 — 심각한 하락세입니다.")
    elif g_revenue == "주의":
        warnings.append(f"매출이 전년 대비 {trend['yoy_change_pct']:.1f}% 감소 — 추세 모니터링이 필요합니다.")

    if g_volatility == "경보":
        warnings.append("매출 변동성이 매우 높습니다 — 안정적인 고객 기반 확보가 필요합니다.")
    elif g_volatility == "주의":
        warnings.append("매출 변동성이 다소 높습니다.")

    if g_competition == "경보":
        warnings.append("업종·상권 경쟁강도가 매우 높습니다 — 차별화 전략이 시급합니다.")
    elif g_competition == "주의":
        warnings.append("경쟁자 유입이 증가하는 추세입니다.")

    if g_location == "경보":
        warnings.append("상권 입지 점수가 낮습니다 — 유동인구 감소 또는 상권 쇠퇴 가능성이 있습니다.")
    elif g_location == "주의":
        warnings.append("상권 입지 환경이 다소 취약합니다.")

    if not warnings:
        warnings.append("현재 주요 위험 징후가 없습니다. 꾸준히 모니터링하세요.")

    return {
        "overall_score":   total,
        "overall_grade":   overall,
        "factors": {
            "매출 추세":  {"score": s_revenue,    "grade": g_revenue,    "value": f"전년비 {trend['yoy_change_pct']:+.1f}%"},
            "변동성":    {"score": s_volatility,  "grade": g_volatility,  "value": f"{volatility:.3f}"},
            "경쟁강도":  {"score": s_competition, "grade": g_competition, "value": f"{competition:.2f}"},
            "입지 점수": {"score": s_location,    "grade": g_location,    "value": str(location)},
        },
        "warnings":       warnings,
        "trend":          trend,
        "exit_signal":    overall == "경보",
        "suggest_exit_within_months": 6 if overall == "경보" else (18 if overall == "주의" else None),
    }
