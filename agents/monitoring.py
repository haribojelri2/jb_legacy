"""Monitoring Agent — 폐업 조기경보 + 이상거래 탐지를 그래프 노드로 통합.

early_warning(경영 건강 점수)과 fraud_guard(이상거래)는 결정론 룰 기반이라
LLM 없이 빠르게 실행된다. 그래프 fan-out에 편입해 탐지 결과(exit_signal·이상거래)를
state에 실어 synthesizer 권고와 family_bridge 알림에 반영한다.
"""

from agents.state import AgentState
from agents.early_warning import calc_health_score
from agents.fraud_guard import analyze_transactions, build_family_alert


def monitoring_agent(state: AgentState) -> dict:
    # 미선택 시 그래프 conditional fan-out이 노드 자체를 실행하지 않음 (graph._route_dispatch)
    profile = state.get("user_profile", {})
    user_id = state.get("user_id", "")
    biz = profile.get("business", {})

    health = calc_health_score(user_id, monthly_profit_override=biz.get("monthly_profit", 0))
    tx = analyze_transactions(user_id)
    alerts = tx.get("alerts", []) if tx else []

    out: dict = {"active_agents": ["EarlyWarning"]}
    if health:
        out["health_score"] = health
    if tx:
        out["fraud_alerts"] = tx
        if alerts:
            out["family_alert_message"] = build_family_alert(profile, alerts)
    return out
