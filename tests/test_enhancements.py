"""고도화 기능 테스트: params.yaml 외부화 · 개인/법인 승계 분기 · 감사추적 DB."""

from config.params import PARAMS
from tools.calculators import resolve_succession_tax


def test_params_loaded_and_wired():
    """params.yaml이 로드되고 핵심 세율·공제가 골든값과 일치한다."""
    for section in ("income_tax", "gift_tax_special", "gift_tax_general",
                    "monte_carlo", "wm", "goodwill"):
        assert section in PARAMS
    assert PARAMS["gift_tax_special"]["deduction"] == 1_000_000_000   # 10억 공제
    assert PARAMS["gift_tax_special"]["min_years"] == 10
    assert PARAMS["income_tax"]["brackets"][0][1] == 0.06             # 최저구간 6%
    assert PARAMS["monte_carlo"]["inflation_rate"] == 0.02            # 물가 2%
    assert PARAMS["goodwill"]["multiples"]["over_20y"] == 36


def test_succession_entity_branch():
    """가업승계 세금이 가업 10년 요건 + 개인/법인 형태로 분기된다."""
    # 10년 이상 + 법인 → 특례 직접 적용
    corp = resolve_succession_tax(312_000_000, 30, "법인")
    assert corp["eligible"] and corp["label"] == "가업승계 과세특례"

    # 10년 이상 + 개인 → 법인 전환 후 특례 (특례 금액 유지 + 직접 승계 일반증여세 병기)
    indiv = resolve_succession_tax(312_000_000, 30, "개인")
    assert indiv["eligible"] and "법인 전환" in indiv["label"]
    assert indiv["total_tax"] == corp["total_tax"]           # 특례 절세액 동일
    assert indiv["direct_general_tax"] > indiv["total_tax"]  # 직접 승계는 더 비쌈

    # 10년 미만 → 특례 대상 아님, 일반 증여세
    under = resolve_succession_tax(88_000_000, 5, "개인")
    assert not under["eligible"] and "일반 증여세" in under["label"]


def test_audit_trail_roundtrip():
    """분석 상태를 감사추적 테이블에 적재하고 그대로 조회된다."""
    from agents.audit import fetch_audit_trail, log_audit
    log_audit("test_audit_user", "가게를 딸한테 넘길지 팔지", {
        "tax_rag_context": "[출처 1] 조특법 제30조의6 ...",
        "compliance_feedback": "OK 금소법 검수 통과",
        "gan_verdict": "통과", "gan_score": 80, "recommended_scenario": "C",
    })
    rows = fetch_audit_trail(limit=1, user_id="test_audit_user")
    assert rows, "감사 레코드가 적재되어야 함"
    r = rows[0]
    assert r["final_scenario"] == "C"
    assert r["gan_score"] == 80 and r["gan_verdict"] == "통과"
    assert r["rag_sources"] == "[출처 1]"
    assert len(r["question_hash"]) == 16
