"""Contract Manager — 10년 자문료 자동이체 계약 & 생애주기 알림 시뮬레이션 (DEMO MOCK).

본선에서 JB은행 자동이체 API + 고객 알림 서비스 연동 예정.
현재는 계약 조건 기반 시뮬레이션 데이터를 사용.
"""

from datetime import date, timedelta
from data.mock_data import USERS


_LIFECYCLE_EVENTS = {
    "lee_sajang": [
        {"years_later": 0,  "event": "계약 체결 & 첫 자문료 수취",          "type": "start"},
        {"years_later": 1,  "event": "세무신고 — 자문료 기타소득 신고 안내",   "type": "tax"},
        {"years_later": 2,  "event": "자녀 운영 2년차 — 경영 현황 점검 권고", "type": "review"},
        {"years_later": 5,  "event": "중간 점검 — 배우자 건강·생활비 재조정",  "type": "review"},
        {"years_later": 7,  "event": "주택연금 재검토 시점 (금리 변동 반영)",  "type": "pension"},
        {"years_later": 10, "event": "자문료 계약 종료 — 자산 재배분 상담 권고","type": "end"},
    ],
}

_DEFAULT_EVENTS = [
    {"years_later": 0,  "event": "계약 체결 & 첫 자문료 수취",           "type": "start"},
    {"years_later": 1,  "event": "세무신고 — 자문료 기타소득 신고 안내",    "type": "tax"},
    {"years_later": 5,  "event": "중간 점검 — 생활비·건강 상태 재조정",    "type": "review"},
    {"years_later": 10, "event": "자문료 계약 종료 — 자산 재배분 상담 권고", "type": "end"},
]

_EVENT_COLOR = {
    "start":   "#5b21b6",
    "tax":     "#f59e0b",
    "review":  "#0369a1",
    "pension": "#16a34a",
    "end":     "#374151",
}


def build_contract_plan(
    user_id: str,
    consulting_monthly: int,
    consulting_rate: float,
    contract_years: int = 10,
    start_date: date | None = None,
) -> dict:
    """자동이체 계약 플랜 + 생애주기 이벤트 타임라인 생성."""
    profile    = USERS.get(user_id, {})
    age        = profile.get("age", 62)
    start      = start_date or date.today()

    total_income   = consulting_monthly * 12 * contract_years
    annual_income  = consulting_monthly * 12
    tax_rate_est   = 0.033   # 기타소득세 3.3% (원천징수)
    tax_annual     = int(annual_income * tax_rate_est)
    net_annual     = annual_income - tax_annual
    net_total      = net_annual * contract_years

    # 연도별 수령 스케줄
    schedule = []
    for yr in range(contract_years + 1):
        yr_date  = start.replace(year=start.year + yr)
        schedule.append({
            "year":         yr,
            "age":          age + yr,
            "date":         yr_date.strftime("%Y-%m"),
            "annual_gross": annual_income if yr < contract_years else 0,
            "annual_net":   net_annual    if yr < contract_years else 0,
            "cumulative":   net_annual * min(yr, contract_years),
        })

    # 생애주기 이벤트
    events_raw = _LIFECYCLE_EVENTS.get(user_id, _DEFAULT_EVENTS)
    events = []
    for e in events_raw:
        ev_date = start.replace(year=start.year + e["years_later"])
        events.append({
            **e,
            "date":  ev_date.strftime("%Y년 %m월"),
            "age":   age + e["years_later"],
            "color": _EVENT_COLOR.get(e["type"], "#374151"),
        })

    return {
        "consulting_monthly":    consulting_monthly,
        "consulting_rate":       consulting_rate,
        "contract_years":        contract_years,
        "start_date":            start.strftime("%Y-%m-%d"),
        "total_gross":           total_income,
        "total_net":             net_total,
        "annual_gross":          annual_income,
        "annual_net":            net_annual,
        "tax_annual_estimate":   tax_annual,
        "schedule":              schedule,
        "lifecycle_events":      events,
        "jb_auto_transfer_note": "JB은행 자동이체 등록 시 매월 자문료 자동 수취. 본선에서 API 연동 예정.",
        "data_source":           "DEMO MOCK — 본선 JB은행 자동이체 API 연동 예정",
    }
