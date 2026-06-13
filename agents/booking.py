"""Booking Agent — JB금융 PB·세무사 상담 예약."""

import os
from datetime import datetime, timedelta
from agents.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState

_BRANCHES = {
    "전주": {"branch": "전북은행 전주본점 WM센터", "address": "전북 전주시 완산구 전주객사3길 99", "tel": "063-250-5000"},
    "서울": {"branch": "전북은행 서울지점 PB센터", "address": "서울 영등포구 국제금융로 10", "tel": "02-6336-7000"},
}

_BOOK_SYSTEM = """\
당신은 JB Legacy 예약 안내 도우미입니다.
상담 예약 내용을 간결하고 따뜻하게 확인해주세요.
예약 일시, 담당자, 준비서류를 포함해 안내하세요."""


def booking_agent(state: AgentState) -> dict:
    query = state.get("query", "")
    selected = state.get("selected_agents", [])
    compliance_fb = state.get("compliance_feedback", "")

    needs_booking = (
        "Booking" in selected
        or any(kw in query for kw in ["예약", "상담", "만나", "방문", "연결", "세무사", "PB"])
        or (compliance_fb and not compliance_fb.startswith("✅") and state.get("retry_count", 0) >= 2)
    )

    if not needs_booking:
        return {"booking_result": {}, "active_agents": ["Booking"]}

    profile = state.get("user_profile", {})
    location = profile.get("location", "전주")
    branch_key = "서울" if "서울" in location else "전주"
    branch_info = _BRANCHES[branch_key]

    # 다음 영업일 오후 2시 예약
    now = datetime.now()
    days_ahead = 1 if now.weekday() < 4 else (7 - now.weekday())
    appt_date = (now + timedelta(days=days_ahead)).strftime("%Y년 %m월 %d일")
    appt_time = "오후 2:00"

    booking = {
        "confirmed": True,
        "branch": branch_info["branch"],
        "address": branch_info["address"],
        "tel": branch_info["tel"],
        "date": appt_date,
        "time": appt_time,
        "consultant": "PB팀 담당 세무사·자산관리사",
        "prep_docs": ["사업자등록증", "최근 3년 소득세 신고서", "임대차계약서", "신분증"],
    }

    llm = get_llm("fast")
    confirm_msg = llm.invoke([
        SystemMessage(content=_BOOK_SYSTEM),
        HumanMessage(content=(
            f"예약 정보:\n"
            f"- 지점: {branch_info['branch']}\n"
            f"- 일시: {appt_date} {appt_time}\n"
            f"- 준비서류: {', '.join(booking['prep_docs'])}\n"
            f"고객명: {profile.get('name', '고객')} / 상담 목적: {query[:80]}"
        )),
    ]).content

    booking["confirm_message"] = confirm_msg

    return {"booking_result": booking, "active_agents": ["Booking"]}
