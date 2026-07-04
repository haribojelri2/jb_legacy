"""supervisor·compliance 결정론 로직 단위 테스트 — LLM 스텁으로 API 없이 검증.

get_llm을 canned-response 스텁으로 교체해(단일 팩토리라 fixture 하나로 전 에이전트 커버)
라우팅 게이트·검수 분기 등 결정론 부분만 검증한다.
"""

import pytest

import agents.supervisor as supervisor_mod
from agents.supervisor import supervisor_agent, RouteDecision
from graph import _route_dispatch, _route_compliance, _needs_booking


class _StubStructured:
    """with_structured_output(RouteDecision) 반환을 흉내내는 스텁."""
    def __init__(self, agents):
        self._agents = agents

    def invoke(self, _messages):
        return RouteDecision(agents=self._agents)


class _StubLLM:
    def __init__(self, agents):
        self._agents = agents

    def with_structured_output(self, _schema):
        return _StubStructured(self._agents)


@pytest.fixture
def stub_supervisor(monkeypatch):
    """supervisor의 get_llm이 지정한 에이전트 목록을 반환하도록 스텁."""
    def _set(agents):
        monkeypatch.setattr(supervisor_mod, "get_llm", lambda tier="fast": _StubLLM(agents))
    return _set


# ── supervisor 라우팅 게이트 ──────────────────────────────────────────────

def test_family_gate_requires_noun_and_verb(stub_supervisor):
    """(가족 명사 AND 공유 동사)일 때만 FamilyBridge 추가."""
    stub_supervisor(["PostExitWM"])
    out = supervisor_agent({"query": "이 결과를 딸에게 공유해줘"})
    assert "FamilyBridge" in out["selected_agents"]


def test_family_gate_not_triggered_by_verb_alone(stub_supervisor):
    """'알려줘'만으로는 FamilyBridge가 발동하지 않아야 함 (오발송 방지)."""
    stub_supervisor(["PostExitWM"])
    out = supervisor_agent({"query": "노후 생활비 알려줘"})
    assert "FamilyBridge" not in out["selected_agents"]


def test_monitoring_gate(stub_supervisor):
    """경영·이상거래 키워드 시 EarlyWarning 추가."""
    stub_supervisor(["BusinessValuation"])
    out = supervisor_agent({"query": "요즘 경영 상태랑 이상거래 점검해줘"})
    assert "EarlyWarning" in out["selected_agents"]


def test_core_fallback_when_none_selected(stub_supervisor):
    """LLM이 핵심 에이전트를 하나도 안 고르면 코어 3개 기본 투입."""
    stub_supervisor([])
    out = supervisor_agent({"query": "어떻게 해야 할지 모르겠어요"})
    assert set(out["selected_agents"]) >= {"BusinessValuation", "TaxSuccession", "PostExitWM"}


# ── 그래프 라우팅 함수 (순수 결정론) ──────────────────────────────────────

def test_route_dispatch_only_selected():
    """선택된 에이전트 노드만 fan-out 대상이 된다."""
    nodes = _route_dispatch({"selected_agents": ["TaxSuccession"]})
    assert nodes == ["tax_succession"]


def test_route_dispatch_empty_goes_synthesizer():
    """선택이 비면 synthesizer로 직행 (빈 fan-out 방지)."""
    assert _route_dispatch({"selected_agents": []}) == ["synthesizer"]


def test_route_compliance_pass_and_retry():
    assert _route_compliance({"compliance_passed": True}) == "pass"
    assert _route_compliance({"compliance_passed": False, "retry_count": 0}) == "retry"


def test_route_compliance_exhausts_retries():
    """재시도 3회 초과면 미통과라도 pass로 라우팅(무한 루프 방지)."""
    assert _route_compliance({"compliance_passed": False, "retry_count": 3}) == "pass"


def test_needs_booking_keyword():
    assert _needs_booking({"query": "PB 상담 예약하고 싶어요"})
    assert not _needs_booking({"query": "세금이 얼마인가요"})
