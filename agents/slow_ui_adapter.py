"""Slow UI Adapter — 어르신 UI용 응답 포맷 변환."""

import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState


def slow_ui_adapter(state: AgentState) -> dict:
    if state.get("ui_mode") != "slow":
        return {}

    raw = state.get("final_response", "")
    if not raw:
        return {}

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    adapted = llm.invoke([
        SystemMessage(content=(
            "62세 자영업자 어르신과 대화하는 친절한 금융 도우미입니다.\n"
            "규칙: 문장 짧고 쉽게 / 어려운 세금 용어는 쉬운 말로 풀어서 / "
            "핵심은 ★ 강조 / 마지막에 '궁금한 게 있으시면 말씀해 주세요 :)' 추가"
        )),
        HumanMessage(content=f"아래 내용을 어르신께 전달해주세요:\n{raw}"),
    ]).content

    return {"final_response": adapted, "final_response_raw": raw}
