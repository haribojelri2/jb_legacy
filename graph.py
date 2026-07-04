"""JB Legacy — LangGraph 멀티 에이전트 오케스트레이터.

흐름:
  supervisor → profiler
      ↓ clarification_needed?
      YES → END  (사용자에게 추가 질문 반환)
      NO  ↓ (병렬 fan-out — selected_agents 기반 선택 실행)
  BusinessValuation ─┐
  TaxSuccession ─────┤→ synthesizer → slow_ui → compliance
  PostExitWM ────────┤      ↓ retry?
  Negotiation ───────┘  YES → synthesizer   NO → family_bridge → booking → END

Agent 동작 구조 (이해 - 판단 - 행동 - 검증/개선):
  이해      supervisor(질문 의도 분석), profiler(프로필·삶의 조건 로드)
  판단      투입 에이전트 선택, 정보 충족 여부 판단,
            시나리오 권고 A/B/C/D 택1 (synthesizer 구조화 출력 강제)
  행동      추가 질문(profiler → END), 근거 조회(tax_succession → 세법 RAG),
            수정안 생성(compliance 피드백 → synthesizer 재생성),
            알림(family_bridge / fraud_guard 가족 통지),
            요약(synthesizer·slow_ui·TTS), 예약(booking)
  검증/개선  이중 검증 루프:
            1) compliance 검수(상시) — 미통과 시 지적사항 반영 재생성,
               retry_count >= 3 종료 조건(초과 시 PB 연결 전환)
            2) gan_review 적대 검증(GAN_AUTO=1) — Critic·Defender·Judge 토론 채점,
               '재생성필요' 판정 시 개선 지시 주입 재생성(최대 1회)

개선사항:
  1. 선택적 에이전트 투입: supervisor 결정 → conditional fan-out으로 선택 노드만 실행
  2. SqliteSaver 체크포인터: thread_id별 대화 상태 영속 저장
  3. stream_query: 노드 완료마다 실시간 yield → UI 라이브 업데이트

Python 3.14 ModuleLock 데드락 방지: openai / langchain_openai를
메인 스레드에서 먼저 임포트해 module lock을 해소한 뒤 병렬 스레드 실행.
"""

import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── pre-import: 병렬 스레드 실행 전 OpenAI 모듈 잠금 해소 ──
import openai          # noqa: F401
import langchain_openai  # noqa: F401

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from agents.state import AgentState
from agents.supervisor import supervisor_agent
from agents.profiler import profiler_agent
from agents.business_valuation import business_valuation_agent
from agents.tax_succession import tax_succession_agent
from agents.post_exit_wm import post_exit_wm_agent
from agents.negotiation import negotiation_agent
from agents.synthesizer import synthesizer_agent
from agents.slow_ui_adapter import slow_ui_adapter
from agents.compliance import compliance_agent
from agents.gan_tester import gan_review_agent
from agents.family_bridge import family_bridge_agent
from agents.booking import booking_agent

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jb_legacy_memory.db")

# UI에서 노드 이름 → 한국어 라벨 변환용
NODE_LABELS: dict[str, str] = {
    "supervisor":         "질문 분석",
    "profiler":           "프로필 로딩",
    "dispatch":           "에이전트 배분",
    "business_valuation": "사업체 가치 평가",
    "tax_succession":     "세금·승계 분석",
    "post_exit_wm":       "자산운용 시뮬레이션",
    "negotiation":        "가족 협상 조율",
    "synthesizer":        "종합 의견 생성",
    "slow_ui":            "UI 포맷 변환",
    "compliance":         "금소법 검수",
    "gan_review":         "적대 검증 (GAN)",
    "family_bridge":      "가족 리포트 공유",
    "booking":            "상담 예약",
}


def _dispatch(state: AgentState) -> dict:
    """profiler → 병렬 domain agents 진입점 (pass-through)."""
    return {}


_AGENT_NODE_MAP = {
    "BusinessValuation": "business_valuation",
    "TaxSuccession":     "tax_succession",
    "PostExitWM":        "post_exit_wm",
    "Negotiation":       "negotiation",
}


def _route_dispatch(state: AgentState) -> list[str]:
    """supervisor가 선택한 에이전트 노드만 실제 실행 (동적 병렬 fan-out).

    미선택 노드는 실행 자체가 안 되므로 self-skip 가드·불필요한 스트림 이벤트가 없다.
    """
    nodes = [_AGENT_NODE_MAP[a] for a in state.get("selected_agents", []) if a in _AGENT_NODE_MAP]
    return nodes or ["synthesizer"]


def _route_after_profiler(state: AgentState) -> str:
    return "clarify" if state.get("clarification_needed") else "continue"


def _route_compliance(state: AgentState) -> str:
    if state.get("compliance_passed") or state.get("retry_count", 0) >= 3:
        return "pass"
    return "retry"


def _needs_booking(state: AgentState) -> bool:
    q = state.get("query", "")
    return any(kw in q for kw in ["예약", "상담 받고", "만나", "방문", "세무사 연결", "PB 연결"])


def build_graph(db_path: str = _DB_PATH):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    saver = SqliteSaver(conn)

    g = StateGraph(AgentState)

    g.add_node("supervisor",         supervisor_agent)
    g.add_node("profiler",           profiler_agent)
    g.add_node("dispatch",           _dispatch)
    g.add_node("business_valuation", business_valuation_agent)
    g.add_node("tax_succession",     tax_succession_agent)
    g.add_node("post_exit_wm",       post_exit_wm_agent)
    g.add_node("negotiation",        negotiation_agent)
    g.add_node("synthesizer",        synthesizer_agent)
    g.add_node("slow_ui",            slow_ui_adapter)
    g.add_node("compliance",         compliance_agent)
    g.add_node("gan_review",         gan_review_agent)
    g.add_node("family_bridge",      family_bridge_agent)
    g.add_node("booking",            booking_agent)

    g.set_entry_point("supervisor")
    g.add_edge("supervisor", "profiler")

    g.add_conditional_edges(
        "profiler",
        _route_after_profiler,
        {"clarify": END, "continue": "dispatch"},
    )

    # 동적 병렬 fan-out: supervisor가 선택한 노드만 실행 (conditional edges 리스트 반환)
    g.add_conditional_edges(
        "dispatch",
        _route_dispatch,
        ["business_valuation", "tax_succession", "post_exit_wm", "negotiation", "synthesizer"],
    )

    # 병렬 fan-in
    g.add_edge("business_valuation", "synthesizer")
    g.add_edge("tax_succession",     "synthesizer")
    g.add_edge("post_exit_wm",       "synthesizer")
    g.add_edge("negotiation",        "synthesizer")

    g.add_edge("synthesizer", "slow_ui")
    g.add_edge("slow_ui", "compliance")
    # 검증 2계층: 금소법 검수(상시) → 적대 검증 GAN(GAN_AUTO=1 시 심층 실행)
    g.add_conditional_edges(
        "compliance",
        _route_compliance,
        {"retry": "synthesizer", "pass": "gan_review"},
    )
    g.add_conditional_edges(
        "gan_review",
        lambda s: "retry" if s.get("gan_regen_needed") else "pass",
        {"retry": "synthesizer", "pass": "family_bridge"},
    )
    g.add_conditional_edges(
        "family_bridge",
        lambda s: "book" if _needs_booking(s) else "skip",
        {"book": "booking", "skip": END},
    )
    g.add_edge("booking", END)

    return g.compile(checkpointer=saver)


def _initial_state(
    user_id: str,
    query: str,
    clarification_answer: str = "",
    life_inputs: dict | None = None,
    daughter_inputs: dict | None = None,
) -> dict:
    return {
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
        "gan_score":             0,
        "gan_verdict":           "",
        "gan_regen_needed":      False,
        "gan_retry_count":       0,
        "clarification_needed":  "",
        "clarification_answer":  clarification_answer,
        "life_inputs":           life_inputs or {},
        "booking_result":        {},
        "daughter_inputs":       daughter_inputs or {},
        "negotiation_result":    {},
        "final_response":        "",
        "final_response_raw":    "",
        "ui_mode":               "normal",
        "active_agents":         [],
    }


def run_query(
    user_id: str,
    query: str,
    clarification_answer: str = "",
    life_inputs: dict | None = None,
    thread_id: str | None = None,
    daughter_inputs: dict | None = None,
) -> AgentState:
    app = build_graph()
    config = {"configurable": {"thread_id": thread_id or user_id}}
    return app.invoke(
        _initial_state(user_id, query, clarification_answer, life_inputs, daughter_inputs),
        config=config,
    )


def stream_query(
    user_id: str,
    query: str,
    clarification_answer: str = "",
    life_inputs: dict | None = None,
    thread_id: str | None = None,
    daughter_inputs: dict | None = None,
):
    """각 노드 완료 시 (node_name, state_update) yield.
    마지막에 ("__done__", full_state) yield.
    """
    app = build_graph()
    config = {"configurable": {"thread_id": thread_id or user_id}}
    for chunk in app.stream(
        _initial_state(user_id, query, clarification_answer, life_inputs, daughter_inputs),
        config=config,
        stream_mode="updates",
    ):
        for node_name, update in chunk.items():
            yield node_name, update

    snapshot = app.get_state(config)
    yield "__done__", snapshot.values
