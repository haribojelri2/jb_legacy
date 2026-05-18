"""Family Bridge — 자녀(이과장)에게 승계 리포트 공유."""

from agents.state import AgentState
from data.mock_data import USERS


def family_bridge_agent(state: AgentState) -> dict:
    if "FamilyBridge" not in state.get("selected_agents", []):
        return {"family_notified": False, "family_message": ""}

    profile = state.get("user_profile", {})
    family_ids = profile.get("family", [])
    children = [USERS.get(fid, {}).get("name", fid) for fid in family_ids]
    child_name = children[0] if children else "자녀"

    tax = state.get("tax_comparison", {})
    portfolio = state.get("retirement_portfolio", {})

    summary_parts = [f"📋 {profile.get('name')} 아버님의 은퇴·가업승계 시뮬레이션 리포트를 공유합니다."]
    if tax:
        sale_tax = tax.get("sale", {}).get("total_tax", 0)
        special_tax = tax.get("special", {}).get("total_tax", 0)
        summary_parts.append(f"• 외부 매각 시 세금: 약 {sale_tax:,}원")
        summary_parts.append(f"• 가업승계 특례 적용 시 세금: 약 {special_tax:,}원")
    if portfolio:
        monthly = portfolio.get("monthly_income", {}).get("합계", 0)
        summary_parts.append(f"• 은퇴 후 예상 월 수령액: 약 {monthly:,}원")

    message = "\n".join(summary_parts)
    alert = f"📱 {child_name}의 JB 앱으로 리포트 발송 완료"

    return {
        "family_notified": True,
        "family_message": f"{alert}\n\n{message}",
        "active_agents": ["FamilyBridge"],
    }
