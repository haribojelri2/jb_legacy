"""JB Legacy — LangGraph 멀티 에이전트 오케스트레이터.

흐름:
  supervisor → profiler
      ↓ clarification_needed?
      YES → END  (사용자에게 추가 질문 반환)
      NO  ↓ (병렬 fan-out via dispatch)
  BusinessValuation ─┐
  TaxSuccession ─────┤→ synthesizer → slow_ui → compliance
  PostExitWM ────────┘      ↓ retry?
                      YES → synthesizer   NO → family_bridge → booking → END

Python 3.14 ModuleLock 데드락 방지: openai / langchain_openai를
메인 스레드에서 먼저 임포트해 module lock을 해소한 뒤 병렬 스레드 실행.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── pre-import: 병렬 스레드 실행 전 OpenAI 모듈 잠금 해소 ──
import openai          # noqa: F401
import langchain_openai  # noqa: F401

from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.supervisor import supervisor_agent
from agents.profiler import profiler_agent
from agents.business_valuation import business_valuation_agent
from agents.tax_succession import tax_succession_agent
from agents.post_exit_wm import post_exit_wm_agent
from agents.synthesizer import synthesizer_agent
from agents.slow_ui_adapter import slow_ui_adapter
from agents.compliance import compliance_agent
from agents.family_bridge import family_bridge_agent
from agents.booking import booking_agent


def _dispatch(state: AgentState) -> dict:
    """profiler → 병렬 domain agents 진입점 (pass-through)."""
    return {}


def _route_after_profiler(state: AgentState) -> str:
    """추가 질문이 필요하면 바로 종료, 아니면 도메인 에이전트 투입."""
    return "clarify" if state.get("clarification_needed") else "continue"


def _needs_booking(state: AgentState) -> bool:
    q = state.get("query", "")
    return any(kw in q for kw in ["예약", "상담 받고", "만나", "방문", "세무사 연결", "PB 연결"])


def _route_compliance(state: AgentState) -> str:
    if state.get("compliance_passed") or state.get("retry_count", 0) >= 3:
        return "pass"
    return "retry"


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("supervisor",         supervisor_agent)
    g.add_node("profiler",           profiler_agent)
    g.add_node("dispatch",           _dispatch)
    g.add_node("business_valuation", business_valuation_agent)
    g.add_node("tax_succession",     tax_succession_agent)
    g.add_node("post_exit_wm",       post_exit_wm_agent)
    g.add_node("synthesizer",        synthesizer_agent)
    g.add_node("slow_ui",            slow_ui_adapter)
    g.add_node("compliance",         compliance_agent)
    g.add_node("family_bridge",      family_bridge_agent)
    g.add_node("booking",            booking_agent)

    g.set_entry_point("supervisor")
    g.add_edge("supervisor", "profiler")

    # 추가 질문 필요 여부 분기
    g.add_conditional_edges(
        "profiler",
        _route_after_profiler,
        {"clarify": END, "continue": "dispatch"},
    )

    # 병렬 fan-out: dispatch → 3개 도메인 에이전트 동시 실행
    g.add_edge("dispatch", "business_valuation")
    g.add_edge("dispatch", "tax_succession")
    g.add_edge("dispatch", "post_exit_wm")

    # 병렬 fan-in: 3개 에이전트 완료 후 synthesizer
    g.add_edge("business_valuation", "synthesizer")
    g.add_edge("tax_succession",     "synthesizer")
    g.add_edge("post_exit_wm",       "synthesizer")

    g.add_edge("synthesizer", "slow_ui")
    g.add_edge("slow_ui", "compliance")
    g.add_conditional_edges(
        "compliance",
        _route_compliance,
        {"retry": "synthesizer", "pass": "family_bridge"},
    )
    g.add_conditional_edges(
        "family_bridge",
        lambda s: "book" if _needs_booking(s) else "skip",
        {"book": "booking", "skip": END},
    )
    g.add_edge("booking", END)

    return g.compile()


def run_query(user_id: str, query: str,
              clarification_answer: str = "",
              life_inputs: dict | None = None) -> AgentState:
    app = build_graph()
    return app.invoke({
        "messages":              [{"role": "user", "content": query}],
        "user_id":               user_id,
        "query":                 query,
        "route":                 "",
        "selected_agents":       [],
        "user_profile":          {},
        "business_valuation":    {},
        "tax_comparison":        {},
        "tax_rag_context":       "",
        "retirement_portfolio":  {},
        "family_notified":       False,
        "family_message":        "",
        "compliance_passed":     False,
        "compliance_feedback":   "",
        "retry_count":           0,
        "clarification_needed":  "",
        "clarification_answer":  clarification_answer,
        "life_inputs":           life_inputs or {},
        "booking_result":        {},
        "final_response":        "",
        "final_response_raw":    "",
        "ui_mode":               "normal",
        "active_agents":         [],
    })
