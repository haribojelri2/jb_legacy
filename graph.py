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

import sys, os, sqlite3, time, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── pre-import: 병렬 스레드 실행 전 OpenAI 모듈 잠금 해소 ──
import openai          # noqa: F401
import langchain_openai  # noqa: F401

# ── 관측성: 노드별 지연·재시도·검수 결과 구조화 로깅 (JB_LOG=1일 때) ──
logger = logging.getLogger("jb_legacy.graph")
if os.getenv("JB_LOG") == "1" and not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)


def _observe(node_name: str, fn):
    """노드 함수를 감싸 진입/퇴출·소요시간·핵심 상태를 로깅."""
    def _wrapped(state):
        t0 = time.perf_counter()
        result = fn(state)
        if logger.isEnabledFor(logging.INFO):
            ms = (time.perf_counter() - t0) * 1000
            extra = ""
            if node_name == "compliance":
                extra = f" passed={result.get('compliance_passed')} retry={result.get('retry_count', state.get('retry_count', 0))}"
            elif node_name == "gan_review":
                extra = f" verdict={result.get('gan_verdict')} score={result.get('gan_score')} regen={result.get('gan_regen_needed')}"
            elif node_name == "supervisor":
                extra = f" agents={result.get('selected_agents')}"
            logger.info(f"{node_name:18} {ms:7.0f}ms{extra}")
        return result
    return _wrapped

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from agents.state import AgentState
from agents.supervisor import supervisor_agent
from agents.profiler import profiler_agent
from agents.business_valuation import business_valuation_agent
from agents.tax_succession import tax_succession_agent
from agents.post_exit_wm import post_exit_wm_agent
from agents.negotiation import negotiation_agent
from agents.monitoring import monitoring_agent
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
    "monitoring":         "경영 건강·이상거래 점검",
    "synthesizer":        "종합 의견 생성",
    "slow_ui":            "UI 포맷 변환",
    "compliance":         "금소법 검수",
    "gan_review":         "적대 검증 (GAN)",
    "escalation":         "PB 상담 전환",
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
    "EarlyWarning":      "monitoring",
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
    if state.get("compliance_passed"):
        return "pass"
    if state.get("retry_count", 0) >= 3:
        return "escalate"   # 재시도 소진 & 미통과 → 실패 응답 차단하고 PB 상담 전환
    return "retry"


_ESCALATION_MESSAGE = (
    "죄송합니다. 정확하고 안전한 안내를 위해 이 분석은 전문가의 직접 검토가 필요합니다.\n\n"
    "AI 자동 검수(금소법·세무 면책)를 통과하지 못해, 확정되지 않은 내용을 그대로 안내드리지 않습니다.\n"
    "담당 PB·세무사와의 상담을 연결해 드리니 아래 예약 정보를 확인해 주세요.\n\n"
    "[주의사항]\n"
    "1. 본 안내는 참고용이며 최종 판단은 담당 PB·세무사와 함께 하시기 바랍니다.\n"
    "2. 세금·투자 관련 결정 전 반드시 전문가 상담을 받으시기 바랍니다."
)


def escalation_agent(state: AgentState) -> dict:
    """검수 미통과 확정 시 — 실패 응답을 안전한 PB 상담 안내로 교체하고 booking 강제."""
    return {
        "final_response": _ESCALATION_MESSAGE,
        "final_response_raw": _ESCALATION_MESSAGE,
        "escalated": True,
        "active_agents": ["Escalation"],
    }


def _needs_booking(state: AgentState) -> bool:
    q = state.get("query", "")
    return any(kw in q for kw in ["예약", "상담 받고", "만나", "방문", "세무사 연결", "PB 연결"])


def build_graph(db_path: str = _DB_PATH):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    saver = SqliteSaver(conn)

    g = StateGraph(AgentState)

    g.add_node("supervisor",         _observe("supervisor", supervisor_agent))
    g.add_node("profiler",           _observe("profiler", profiler_agent))
    g.add_node("dispatch",           _dispatch)
    g.add_node("business_valuation", _observe("business_valuation", business_valuation_agent))
    g.add_node("tax_succession",     _observe("tax_succession", tax_succession_agent))
    g.add_node("post_exit_wm",       _observe("post_exit_wm", post_exit_wm_agent))
    g.add_node("negotiation",        _observe("negotiation", negotiation_agent))
    g.add_node("monitoring",         _observe("monitoring", monitoring_agent))
    g.add_node("synthesizer",        _observe("synthesizer", synthesizer_agent))
    g.add_node("slow_ui",            _observe("slow_ui", slow_ui_adapter))
    g.add_node("compliance",         _observe("compliance", compliance_agent))
    g.add_node("gan_review",         _observe("gan_review", gan_review_agent))
    g.add_node("escalation",         _observe("escalation", escalation_agent))
    g.add_node("family_bridge",      _observe("family_bridge", family_bridge_agent))
    g.add_node("booking",            _observe("booking", booking_agent))

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
        ["business_valuation", "tax_succession", "post_exit_wm", "negotiation",
         "monitoring", "synthesizer"],
    )

    # 병렬 fan-in (선택 실행된 노드만 실제로 synthesizer를 트리거)
    g.add_edge("business_valuation", "synthesizer")
    g.add_edge("tax_succession",     "synthesizer")
    g.add_edge("post_exit_wm",       "synthesizer")
    g.add_edge("negotiation",        "synthesizer")
    g.add_edge("monitoring",         "synthesizer")

    g.add_edge("synthesizer", "slow_ui")
    g.add_edge("slow_ui", "compliance")
    # 검증 2계층: 금소법 검수(상시) → 적대 검증 GAN(GAN_AUTO=1 시 심층 실행)
    # 검수 미통과가 재시도 소진되면 escalation으로 라우팅해 실패 응답을 차단하고 PB 상담 전환
    g.add_conditional_edges(
        "compliance",
        _route_compliance,
        {"retry": "synthesizer", "pass": "gan_review", "escalate": "escalation"},
    )
    g.add_conditional_edges(
        "gan_review",
        lambda s: "retry" if s.get("gan_regen_needed") else "pass",
        {"retry": "synthesizer", "pass": "family_bridge"},
    )
    g.add_edge("escalation", "booking")   # 검수 실패 → PB 상담 예약 강제
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
        "health_score":          {},
        "fraud_alerts":          {},
        "family_alert_message":  "",
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
        "escalated":             False,
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
    tid = thread_id or user_id
    config = {"configurable": {"thread_id": tid}}
    result = app.invoke(
        _initial_state(user_id, query, clarification_answer, life_inputs, daughter_inputs),
        config=config,
    )
    from agents.audit import log_audit
    log_audit(user_id, query, result, tid)   # 감사 추적 적재
    return result


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
    from agents.audit import log_audit
    log_audit(user_id, query, snapshot.values, thread_id or user_id)   # 감사 추적 적재
    yield "__done__", snapshot.values
