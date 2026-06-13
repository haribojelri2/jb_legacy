"""PB 상담용 PDF 리포트 생성 (fpdf2 + Malgun Gothic).

분석 결과(시나리오 비교·계산 근거·생존 확률 차트·최종 권고)를
A4 PDF로 출력한다. 한글 폰트는 Windows 기본 Malgun Gothic 사용.
"""

import io
import os
import re
import logging
from datetime import datetime

from fpdf import FPDF

# 한글 폰트 subset 시 fontTools가 내는 무해한 경고("MERG NOT subset ... dropped") 억제
logging.getLogger("fontTools").setLevel(logging.ERROR)
logging.getLogger("fontTools.subset").setLevel(logging.ERROR)

_FONT_DIR = r"C:\Windows\Fonts"
_FONT_REGULAR = os.path.join(_FONT_DIR, "malgun.ttf")
_FONT_BOLD = os.path.join(_FONT_DIR, "malgunbd.ttf")

# 이모지·딩뱃 등 Malgun Gothic에 글리프가 없는 문자 제거
_EMOJI_RE = re.compile(
    r"[\U00010000-\U0010FFFF☀-➿⬀-⯿️‍←-⇿]"
)


def _sanitize(text: str) -> str:
    return _EMOJI_RE.sub("", text or "").strip()


def _survival_chart_png(mc_comp: dict) -> bytes | None:
    """monte_carlo_comparison → 생존 확률 곡선 PNG (matplotlib Agg)."""
    curves = {
        f"{label}안": data["survival_curve"]
        for label, data in mc_comp.items()
        if not label.startswith("_") and data
    }
    if not curves:
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(7.0, 3.4), dpi=150)
    for label, curve in curves.items():
        ages = list(curve.keys())
        probs = list(curve.values())
        ax.plot(ages, probs, linewidth=2, label=f"{label} (최종 {probs[-1]:.0f}%)")
    ax.set_xlabel("나이(세)")
    ax.set_ylabel("생존 확률(%)")
    ax.set_title("은퇴 자산 생존 확률 — CPP 의료비 쇼크 몬테카를로")
    ax.set_ylim(-3, 103)
    ax.grid(alpha=0.4, linestyle=":")
    ax.legend()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


class _Report(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Malgun", "", 8)
            self.set_text_color(150)
            self.cell(0, 6, "JB Legacy — 은퇴 설계 분석 리포트", align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0)
            self.ln(2)

    def footer(self):
        self.set_y(-14)
        self.set_font("Malgun", "", 8)
        self.set_text_color(150)
        self.cell(0, 6, f"- {self.page_no()} -", align="C")
        self.set_text_color(0)

    def h1(self, text: str):
        self.set_font("Malgun", "B", 16)
        self.cell(0, 10, _sanitize(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def h2(self, text: str):
        self.ln(3)
        self.set_font("Malgun", "B", 12)
        self.set_text_color(30, 30, 90)
        self.cell(0, 8, _sanitize(text), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0)
        self.ln(1)

    def para(self, text: str, size: int = 9.5):
        self.set_font("Malgun", "", size)
        self.multi_cell(0, 5.4, _sanitize(text))
        self.ln(1)


def build_pdf_report(result: dict, life_inputs: dict, profile: dict) -> bytes:
    """분석 결과 → PDF bytes. 폰트 부재 등 실패 시 예외 발생 (호출부에서 처리)."""
    if not os.path.exists(_FONT_REGULAR):
        raise FileNotFoundError(f"Malgun Gothic 폰트를 찾을 수 없습니다: {_FONT_REGULAR}")

    pdf = _Report(orientation="P", unit="mm", format="A4")
    pdf.add_font("Malgun", "", _FONT_REGULAR)
    pdf.add_font("Malgun", "B", _FONT_BOLD if os.path.exists(_FONT_BOLD) else _FONT_REGULAR)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # ── 표지 헤더 ─────────────────────────────────────────────
    pdf.h1("JB Legacy — 은퇴 설계 분석 리포트")
    pdf.set_font("Malgun", "", 9)
    pdf.set_text_color(110)
    pdf.cell(0, 6, f"생성일: {datetime.now():%Y-%m-%d %H:%M}  |  PB 상담 보조 자료 (AI 추정치)",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)
    pdf.ln(2)

    # ── 1. 고객·사업 프로필 ──────────────────────────────────
    biz = profile.get("business", {})
    personal = profile.get("personal_assets", {})
    pdf.h2("1. 고객·사업 프로필")
    profile_lines = [
        f"고객명: {profile.get('name', '-')} ({profile.get('age', '-')}세, {profile.get('location', '-')})",
        f"업체: {biz.get('name', '-')} — 운영 {biz.get('years_operating', '-')}년, "
        f"월 순이익 {biz.get('monthly_profit', 0):,}원",
        f"개인 자산: 저축 {personal.get('savings', 0):,}원 / 부동산 {personal.get('real_estate', 0):,}원 / "
        f"국민연금 월 {personal.get('pension_monthly_expected', 0):,}원",
    ]
    if life_inputs:
        profile_lines.append(
            "분석 가정: "
            + ", ".join(f"{k}={v:,}" if isinstance(v, int) else f"{k}={v}"
                        for k, v in life_inputs.items())
        )
    pdf.para("\n".join(profile_lines))

    # ── 2. 시나리오 비교 ──────────────────────────────────────
    portfolio = result.get("retirement_portfolio", {})
    scenarios = [
        ("A. 완전 매각", portfolio.get("scenario_sale")),
        ("B. 완전 승계", portfolio.get("scenario_succession")),
        ("C. 절충안", portfolio.get("scenario_hybrid")),
        ("D. 가족 합의안", result.get("negotiation_result", {}).get("scenario_negotiated")),
    ]
    scenarios = [(label, s) for label, s in scenarios if s]
    if scenarios:
        pdf.h2("2. 시나리오 비교")
        recommended = result.get("recommended_scenario", "")
        pdf.set_font("Malgun", "", 9)
        with pdf.table(text_align="CENTER", line_height=6.5) as table:
            head = table.row()
            for col in ["시나리오", "운용자산", "월 수령 합계", "목표 대비", "생존확률(100세)"]:
                head.cell(col)
            for label, s in scenarios:
                row = table.row()
                mark = " (추천)" if recommended and recommended in label[:1] else ""
                mc = s.get("monte_carlo", {})
                row.cell(label + mark)
                row.cell(f"{s.get('total_capital', 0):,}원")
                row.cell(f"{s.get('monthly_income', {}).get('합계', 0):,}원")
                row.cell(f"{s.get('surplus_monthly', 0):+,}원")
                row.cell(f"{mc.get('survival_probability', '-')}%" if mc else "-")
        pdf.ln(2)

    # ── 3. 생존 확률 차트 ─────────────────────────────────────
    mc_comp = portfolio.get("monte_carlo_comparison", {})
    chart = _survival_chart_png(mc_comp)
    if chart:
        pdf.h2("3. 은퇴 자산 생존 확률 (몬테카를로)")
        pdf.image(io.BytesIO(chart), w=170)
        model = mc_comp.get("_model", {})
        if model.get("description"):
            pdf.set_font("Malgun", "", 8)
            pdf.set_text_color(110)
            pdf.multi_cell(0, 4.6, _sanitize(f"모형: {model['description']}"))
            pdf.set_text_color(0)
        pdf.ln(1)

    # ── 4. 계산 근거 (synthesizer와 동일 로직 재사용) ─────────
    from agents.synthesizer import _build_calc_section
    calc_text = _build_calc_section(
        result.get("tax_comparison", {}),
        result.get("business_valuation", {}),
        portfolio.get("scenario_sale"),
        portfolio.get("scenario_succession"),
        portfolio.get("scenario_hybrid"),
    )
    if calc_text:
        pdf.h2("4. 계산 근거")
        pdf.para(calc_text.replace("[계산 근거]", "").strip(), size=8.5)

    # ── 5. 최종 권고 (AI 종합 의견) ──────────────────────────
    final = result.get("final_response_raw") or result.get("final_response", "")
    if final:
        pdf.h2("5. AI 종합 의견")
        pdf.para(final, size=9)

    # ── 6. 주의사항 ──────────────────────────────────────────
    pdf.h2("6. 주의사항")
    pdf.para(
        "1. 본 리포트의 세금·수익 수치는 AI 추정치이며 실제와 다를 수 있습니다.\n"
        "2. 세무사 상담을 권장합니다.\n"
        "3. 투자 상품(펀드·연금)은 원금 손실 가능성이 있으며, 가입 전 위험등급을 확인하시기 바랍니다.\n"
        "4. 최종 결정은 고객 본인과 담당 PB·세무사가 함께 하시기 바랍니다.",
        size=8.5,
    )

    return bytes(pdf.output())
