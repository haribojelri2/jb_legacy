"""compliance 결정론 수치 대조(verify_numbers) 단위 테스트 — LLM 미사용."""

from agents.compliance import verify_numbers

_STATE = {
    "tax_comparison": {
        "sale":    {"total_tax": 28_754_000, "goodwill": 162_000_000},
        "special": {"total_tax": 0},
    },
    "retirement_portfolio": {
        "scenario_sale":       {"monthly_income": {"합계": 2_875_000}},
        "scenario_succession": {"monthly_income": {"합계": 2_890_000}},
    },
}


def test_no_calc_section_skips_check():
    """계산 근거 섹션이 없으면(단일 에이전트·일상 대화) 대조를 생략한다."""
    assert verify_numbers(_STATE, "간단한 답변입니다. 세무사 상담 권장.") == []


def test_all_figures_present_passes():
    resp = (
        "[계산 근거]\n"
        "권리금 162,000,000원, 매각 세금 28,754,000원\n"
        "A안 월수령 2,875,000원, B안 월수령 2,890,000원\n"
    )
    assert verify_numbers(_STATE, resp) == []


def test_mangled_figure_detected():
    """LLM이 세금 금액을 훼손하면 누락으로 감지된다."""
    resp = (
        "[계산 근거]\n"
        "권리금 162,000,000원, 매각 세금 99,999,999원\n"  # 틀린 값
        "A안 월수령 2,875,000원, B안 월수령 2,890,000원\n"
    )
    missing = verify_numbers(_STATE, resp)
    assert any("매각 세금" in m for m in missing)


def test_zero_figure_not_required():
    """0원(특례 공제)은 표기 방식이 다양하므로 대조 대상에서 제외한다."""
    resp = "[계산 근거]\n권리금 162,000,000원 매각 세금 28,754,000원 A안 월수령 2,875,000원 B안 월수령 2,890,000원"
    missing = verify_numbers(_STATE, resp)
    assert not any("증여세" in m for m in missing)
