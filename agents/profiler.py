"""Profiler — 사용자 프로필 로드 + 핵심 정보 누락 시 추가 질문 생성."""

import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState
from data.mock_data import USERS

_REQUIRED_BIZ = {
    "monthly_profit":   "월 순이익이 얼마나 되시나요? (예: 450만원)",
    "years_operating":  "가게를 몇 년째 운영하고 계신가요?",
    "goodwill":         "권리금(또는 예상 매도가)은 얼마 정도로 생각하고 계신가요?",
}

_CLARIFY_SYSTEM = """\
당신은 JB Legacy 상담 도우미입니다.
사용자 질문과 현재 파악된 정보를 비교해, 정확한 분석에 꼭 필요한 정보가 빠져 있으면
한 가지 질문만 짧고 친절하게 물어보세요.
불필요하면 "SUFFICIENT"만 반환하세요."""


def profiler_agent(state: AgentState) -> dict:
    profile = USERS.get(state["user_id"], {})
    ui_mode = "slow" if profile.get("slow_ui") else "normal"
    biz = profile.get("business", {})

    # UI 드롭다운 입력값을 profile에 병합
    life_inputs = state.get("life_inputs", {})
    if life_inputs:
        profile = {**profile, "life_factors": life_inputs}

    if state.get("clarification_answer"):
        return {
            "user_profile": profile,
            "ui_mode": ui_mode,
            "clarification_needed": "",
            "active_agents": ["Profiler"],
        }

    missing = [h for f, h in _REQUIRED_BIZ.items() if not biz.get(f)]
    if missing:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
        known = (
            f"월순이익: {biz.get('monthly_profit','미확인')}, "
            f"운영기간: {biz.get('years_operating','미확인')}년, "
            f"권리금: {biz.get('goodwill','미확인')}"
        )
        resp = llm.invoke([
            SystemMessage(content=_CLARIFY_SYSTEM),
            HumanMessage(content=f"질문: {state['query']}\n현재 파악된 정보: {known}"),
        ]).content.strip()

        if resp != "SUFFICIENT":
            return {
                "user_profile": profile,
                "ui_mode": ui_mode,
                "clarification_needed": resp,
                "final_response": resp,
                "active_agents": ["Profiler"],
            }

    return {
        "user_profile": profile,
        "ui_mode": ui_mode,
        "clarification_needed": "",
        "active_agents": ["Profiler"],
    }
