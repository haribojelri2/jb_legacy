"""Fraud Guard — 이상거래 탐지 + 소비흐름 분석 + 가족 알림 (DEMO MOCK).

대회 지정주제 1의 "이상거래를 탐지하고 가족·보호자에게 알림" 기능.
FDS 표준 패턴을 단순화한 룰 기반 탐지 (데모 재현성을 위해 LLM 미사용):
  R1 고액 이탈 : 평소 지출 분포(평균+3σ) 이탈 및 100만원 초과
  R2 심야 거래 : 00~06시 거래
  R3 분할 결제 : 같은 날 동일 가맹점 반복 결제 합계 200만원 초과 (한도 회피 패턴)
  R4 해외 거래 : 해외 가맹점 거래

향후 JB은행 실시간 거래 스트림·FDS API 연동 예정.
"""

from collections import defaultdict
from statistics import mean, pstdev

from data.db import fetch_transactions

_PERIOD_DAYS = 90
_NIGHT_END_HOUR = 6           # 00:00 ~ 05:59 심야
_HIGH_AMOUNT_FLOOR = 1_000_000
_SPLIT_PAYMENT_SUM = 2_000_000


def analyze_transactions(user_id: str) -> dict:
    """거래내역 → 소비흐름 요약 + 이상거래 경보 목록."""
    txs = fetch_transactions(user_id)
    if not txs:
        return {}

    normal = [t for t in txs if not t["is_anomaly"]]
    base_amounts = [t["amount"] for t in normal] or [t["amount"] for t in txs]

    # R1 임계값: 평소 지출 평균+3σ (최소 100만원)
    high_threshold = max(
        _HIGH_AMOUNT_FLOOR,
        int(mean(base_amounts) + 3 * pstdev(base_amounts)),
    )

    # R3: (일자, 가맹점)별 반복 결제 그룹
    groups = defaultdict(list)
    for t in txs:
        groups[(t["day_offset"], t["merchant"])].append(t)
    split_ids = {
        t["id"]
        for g in groups.values()
        if len(g) >= 2 and sum(t["amount"] for t in g) > _SPLIT_PAYMENT_SUM
        for t in g
    }

    alerts = []
    for t in txs:
        reasons = []
        if t["amount"] >= high_threshold:
            reasons.append(f"평소 지출 대비 고액 ({t['amount']:,}원)")
        if int(t["tx_time"][:2]) < _NIGHT_END_HOUR:
            reasons.append(f"심야 시간대 ({t['tx_time']})")
        if t["id"] in split_ids:
            reasons.append("동일 가맹점 반복 결제 (한도 회피 의심)")
        if "해외" in t["merchant"] or "해외" in t["category"]:
            reasons.append("해외 가맹점 거래")
        if not reasons:
            continue
        alerts.append({
            "day_offset": t["day_offset"],
            "tx_time":    t["tx_time"],
            "merchant":   t["merchant"],
            "channel":    t["channel"],
            "amount":     t["amount"],
            "reasons":    reasons,
            "risk":       "높음" if len(reasons) >= 2 else "주의",
        })
    alerts.sort(key=lambda a: (a["day_offset"], a["tx_time"]))

    # 소비흐름 요약 (이상거래 제외, 월평균 환산)
    months = _PERIOD_DAYS / 30
    category_monthly = defaultdict(int)
    for t in normal:
        category_monthly[t["category"]] += t["amount"]
    category_monthly = {
        c: int(v / months)
        for c, v in sorted(category_monthly.items(), key=lambda kv: -kv[1])
    }

    return {
        "period_days":          _PERIOD_DAYS,
        "tx_count":             len(txs),
        "monthly_spend_normal": int(sum(t["amount"] for t in normal) / months),
        "category_monthly":     category_monthly,
        "alerts":               alerts,
        "high_threshold":       high_threshold,
    }


def build_family_alert(profile: dict, alerts: list[dict]) -> str:
    """보호자(자녀)에게 보낼 이상거래 알림 메시지 (플레인 텍스트)."""
    if not alerts:
        return ""
    name = profile.get("name", "고객")
    total = sum(a["amount"] for a in alerts)
    lines = [
        f"[JB Legacy 거래 안심 알림]",
        f"{name}님 계좌에서 평소와 다른 거래 {len(alerts)}건이 감지되었습니다. (합계 {total:,}원)",
        "",
    ]
    for a in alerts:
        lines.append(
            f"- {a['day_offset']}일 전 {a['tx_time']} | {a['merchant']} | "
            f"{a['amount']:,}원 | 위험도 {a['risk']} ({', '.join(a['reasons'])})"
        )
    lines += [
        "",
        "보이스피싱·금융사기가 의심되면 즉시 해당 거래의 지급정지를 요청하세요.",
        "전북은행 고객센터 063-250-5000 / 경찰청 112",
    ]
    return "\n".join(lines)
