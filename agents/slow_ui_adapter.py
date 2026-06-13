"""Slow UI Adapter — 어르신 UI용 응답 포맷 변환."""

import os
from agents.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import AgentState


def slow_ui_adapter(state: AgentState) -> dict:
    if state.get("ui_mode") != "slow":
        return {}

    raw = state.get("final_response", "")
    if not raw:
        return {}

    # [주의사항] 면책 고지는 LLM 변환에서 제외하고 원문 그대로 보존한다.
    # (시니어 변환 모델이 요약하며 면책 문구를 누락 → 금소법 검수 FAIL 방지)
    _MARK = "[주의사항]"
    if _MARK in raw:
        body, _disc = raw.split(_MARK, 1)
        disclaimer = _MARK + _disc
    else:
        body, disclaimer = raw, ""

    llm = get_llm("fast")
    adapted_body = llm.invoke([
        SystemMessage(content=(
            "62세 자영업자 어르신과 대화하는 친절한 금융 도우미입니다.\n"
            "규칙: 문장 짧고 쉽게 / 어려운 세금 용어는 쉬운 말로 풀어서 / "
            "핵심은 ★ 강조"
        )),
        HumanMessage(content=f"아래 내용을 어르신께 전달해주세요:\n{body}"),
    ]).content

    # 본문(쉬운 말) + 면책 고지(원문 보존) + 마무리 인사
    adapted = adapted_body.rstrip()
    if disclaimer:
        adapted += "\n\n" + disclaimer.strip()
    adapted += "\n\n궁금한 게 있으시면 말씀해 주세요 :)"

    return {"final_response": adapted, "final_response_raw": raw}
