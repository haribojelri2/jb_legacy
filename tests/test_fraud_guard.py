"""agents/fraud_guard.py 단위 테스트 (시드 데이터 ground-truth 대조)."""

from agents.fraud_guard import analyze_transactions, build_family_alert
from data.db import fetch_transactions


def test_seed_transactions_exist():
    txs = fetch_transactions("lee_sajang")
    assert len(txs) >= 40
    assert sum(t["is_anomaly"] for t in txs) == 4   # 시드된 이상거래 라벨


def test_detection_matches_ground_truth():
    """탐지 결과가 라벨과 정확히 일치 — 미탐 0, 오탐 0."""
    txs = fetch_transactions("lee_sajang")
    truth = {(t["day_offset"], t["tx_time"]) for t in txs if t["is_anomaly"]}
    r = analyze_transactions("lee_sajang")
    detected = {(a["day_offset"], a["tx_time"]) for a in r["alerts"]}
    assert detected == truth


def test_all_seeded_anomalies_high_risk():
    """시드된 보이스피싱 패턴은 모두 복수 사유 → 위험도 높음."""
    r = analyze_transactions("lee_sajang")
    assert len(r["alerts"]) == 4
    for a in r["alerts"]:
        assert a["risk"] == "높음"
        assert len(a["reasons"]) >= 2


def test_detection_rules_coverage():
    """4개 룰(고액/심야/분할/해외)이 각각 최소 1건에서 발화."""
    r = analyze_transactions("lee_sajang")
    all_reasons = " | ".join(rs for a in r["alerts"] for rs in a["reasons"])
    assert "고액" in all_reasons
    assert "심야" in all_reasons
    assert "반복 결제" in all_reasons
    assert "해외" in all_reasons


def test_spending_summary_excludes_anomalies():
    """소비흐름 요약은 이상거래를 제외 — 월 생활비가 현실적 범위."""
    r = analyze_transactions("lee_sajang")
    assert 500_000 < r["monthly_spend_normal"] < 3_000_000
    assert "식료품" in r["category_monthly"]
    assert sum(r["category_monthly"].values()) > 0


def test_family_alert_message():
    r = analyze_transactions("lee_sajang")
    msg = build_family_alert({"name": "이사장"}, r["alerts"])
    assert "이사장" in msg
    assert "4건" in msg
    assert "8,000,000원" in msg
    assert "지급정지" in msg
    assert build_family_alert({"name": "이사장"}, []) == ""


def test_unknown_user_returns_empty():
    assert analyze_transactions("no_such_user") == {}
