"""Param Adjuster — 자연어 메시지에서 life_inputs 파라미터 변경을 감지·추출."""

import os, json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

_SYSTEM = """\
사용자 메시지에서 분석 파라미터 변경 요청을 감지하세요.

변경 가능한 파라미터:
- succession: "예" 또는 "아니오" (따님 승계 의향)
- market_trend: "성장" 또는 "보합" 또는 "하락" (지역 상권 트렌드)
- retirement_timeline: "1년 이내" 또는 "3년 이내" 또는 "5년 이상" (은퇴 시점)
- target_monthly: 정수 (월 목표 생활비, 원 단위. 예: "300만원" → 3000000)
- home_pension: "예" 또는 "아니오" (주택연금 활용)

규칙:
1. 파라미터 변경이 감지되면: {"changes": {"파라미터명": "값", ...}, "description": "변경 내용 한 줄 요약"}
2. 변경이 없으면: {"changes": {}, "description": ""}
3. 반드시 JSON만 반환하세요. 다른 텍스트 없이.

예시:
- "자문료를 30%로 바꿔줘" → consulting_rate는 life_inputs에 없으므로 무시
- "은퇴를 5년 후로 미뤘을 때는?" → {"changes": {"retirement_timeline": "5년 이상"}, "description": "은퇴 시점을 5년 이상으로 변경"}
- "상권이 성장세라고 가정하면" → {"changes": {"market_trend": "성장"}, "description": "상권 트렌드를 성장으로 변경"}
- "목표 생활비 250만원으로 낮추면" → {"changes": {"target_monthly": 2500000}, "description": "월 목표 생활비를 250만원으로 변경"}
- "주택연금도 활용하면 어때?" → {"changes": {"home_pension": "예"}, "description": "주택연금 활용으로 변경"}"""


def detect_param_changes(query: str, current_life: dict) -> tuple[dict, str]:
    """(변경된 파라미터 dict, 변경 설명 str) 반환. 변경 없으면 ({}, "")."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    resp = llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=(
            f"현재 설정: {json.dumps(current_life, ensure_ascii=False)}\n"
            f"사용자 메시지: {query}"
        )),
    ]).content.strip()

    try:
        parsed = json.loads(resp)
        return parsed.get("changes", {}), parsed.get("description", "")
    except Exception:
        return {}, ""
