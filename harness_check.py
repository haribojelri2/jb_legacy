"""통합 하네스 러너 — 자동화 가능한 검증을 한 번에 실행.

    python harness_check.py              # 기계적 검사 (단위 테스트 + 정합성 + 배선), 수초
    python harness_check.py --scenario   # 위 + 대표 시나리오 그래프 스모크 (LLM, 수분·API 키 필요)

LLM 추론이 필요한 리뷰(compliance-risk-review, improvement-backlog)는
Claude Code에서 `/harness-all` 또는 개별 `/스킬명`으로 실행한다.
"""

import argparse
import glob
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
results = []  # (통과여부, 항목, 상세)


def _check(ok: bool, name: str, detail: str = ""):
    results.append((ok, name, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" - {detail}" if detail else ""))


def _read(path: str) -> str:
    try:
        return open(os.path.join(ROOT, path), encoding="utf-8").read()
    except Exception:
        return ""


# ── 1. 단위 테스트 ───────────────────────────────────────────────────────────
def run_unit_tests():
    print("\n== 단위 테스트 (pytest, API 불필요) ==")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--ignore=tests/test_ui.py", "-q"],
        cwd=ROOT, capture_output=True, text=True,
    )
    tail = (proc.stdout or "").strip().splitlines()[-1:] or [""]
    _check(proc.returncode == 0, "단위 테스트 전체 통과", tail[0])
    return _extract_test_count()


def _extract_test_count() -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--ignore=tests/test_ui.py", "--co", "-q"],
        cwd=ROOT, capture_output=True, text=True,
    )
    m = re.search(r"(\d+) tests? collected", proc.stdout or "")
    return int(m.group(1)) if m else -1


def _ui_test_count() -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_ui.py", "--co", "-q"],
        cwd=ROOT, capture_output=True, text=True,
    )
    m = re.search(r"(\d+) tests? collected", proc.stdout or "")
    return int(m.group(1)) if m else -1


# ── 2. 문서-코드 정합성 (spec-consistency-check) ─────────────────────────────
def run_spec_consistency(unit_count: int):
    print("\n== 문서-코드 정합성 ==")
    ui_count = _ui_test_count()
    docs = _read("MVP제안서.md") + _read("기능명세서.md")

    # 테스트 수 표기 대조
    claimed = set(int(n) for n in re.findall(r"단위 테스트[^\d]{0,4}(\d+)", docs))
    _check(unit_count in claimed if claimed else False,
           "문서 '단위 테스트 N건' = 실측",
           f"실측 {unit_count} / 문서표기 {sorted(claimed) or '없음'}")

    # 모델명: 문서가 Claude를 언급하는가 (GPT-4o 단독 표기 잔존 탐지)
    llm = _read("agents/llm.py")
    code_claude = "claude" in llm.lower()
    doc_mentions_claude = "claude" in docs.lower()
    _check(code_claude and doc_mentions_claude,
           "LLM 모델 표기 일치 (코드·문서 모두 Claude)",
           f"코드 claude={code_claude} / 문서 claude={doc_mentions_claude}")

    # 골든 수치: 권리금 162,000,000 — 테스트(숫자)와 문서(한글 '1억 6,200만')가 같은 값인지
    test_calc = _read("tests/test_calculators.py")
    code_has = "162,000,000" in test_calc or "162_000_000" in test_calc
    doc_has = ("162,000,000" in docs) or ("1억 6,200만" in docs) or ("162_000_000" in docs)
    _check(code_has and doc_has,
           "골든 권리금 수치 일치 (권리금 1억 6,200만 = 162,000,000)",
           f"코드={code_has} / 문서={doc_has}")

    print(f"     (참고: 화면 자동화 테스트 {ui_count}건)")


# ── 3. Agent 흐름 배선 (agent-flow-review) ───────────────────────────────────
def run_agent_flow():
    print("\n== Agent 흐름 배선 무결성 ==")
    graph = _read("graph.py")

    # agents/*.py 의 *_agent 함수가 graph.py에 등록됐는가 (UI 전용 헬퍼는 제외)
    wired_nodes = set(re.findall(r'add_node\("([a-z_]+)"', graph))
    # graph에 배선돼야 하는 핵심 에이전트 (UI 전용: booking 제외 아님 — booking도 노드)
    core_expected = {
        "supervisor", "profiler", "business_valuation", "tax_succession",
        "post_exit_wm", "negotiation", "synthesizer", "compliance",
        "gan_review", "monitoring", "family_bridge", "booking",
    }
    missing = core_expected - wired_nodes
    _check(not missing, "핵심 에이전트 그래프 배선",
           f"배선 {len(wired_nodes)}개" + (f" / 누락 {missing}" if missing else ""))

    # 검증/개선 루프 요소 존재
    _check("verify_numbers" in _read("agents/compliance.py"),
           "컴플라이언스 결정론 수치 대조(verify_numbers) 존재")
    _check("gan_regen_needed" in _read("agents/gan_tester.py") and "gan_review" in graph,
           "GAN 적대 검증 루프 배선")
    _check("solve_target_monthly" in _read("tools/monte_carlo.py"),
           "goal-seek 역산(solve_target_monthly) 존재")
    _check("max_retries" in _read("agents/llm.py"),
           "LLM 장애 격리(max_retries) 설정")

    # 동적 fan-out: 정적 엣지 + self-skip 잔재가 없는가
    dynamic = "_route_dispatch" in graph and "add_conditional_edges" in graph
    _check(dynamic, "동적 fan-out (conditional edges) 적용")


# ── 4. 대표 시나리오 스모크 (선택, LLM) ──────────────────────────────────────
def run_scenario_smoke():
    print("\n== 대표 시나리오 그래프 스모크 (LLM 호출) ==")
    sys.path.insert(0, ROOT)
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
    if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        _check(False, "시나리오 스모크", "API 키 없음 — 건너뜀")
        return
    from graph import run_query
    cases = [
        ("종합 상담", "폐업할지 승계할지 고민입니다. 세금이랑 노후 생활비까지 분석해주세요."),
        ("세금 단독", "가업승계하면 증여세가 얼마나 나오나요?"),
    ]
    import time
    for i, (label, q) in enumerate(cases):
        t0 = time.time()
        try:
            s = run_query(user_id="lee_sajang", query=q, thread_id=f"hc_{i}")
            fr = s.get("final_response", "")
            md = any(t in fr for t in ("**", "## ", "```"))
            ok = bool(fr) and s.get("compliance_passed") is not False and not md
            _check(ok, f"시나리오: {label}",
                   f"{time.time()-t0:.0f}s len={len(fr)} compliance={s.get('compliance_passed')} md_leak={md}")
        except Exception as e:
            _check(False, f"시나리오: {label}", f"예외 {type(e).__name__}: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", action="store_true", help="대표 시나리오 그래프 스모크 추가 실행(LLM)")
    args = ap.parse_args()

    print("=" * 60)
    print(" JB Legacy 통합 하네스 체크")
    print("=" * 60)

    unit_count = run_unit_tests()
    run_spec_consistency(unit_count)
    run_agent_flow()
    if args.scenario:
        run_scenario_smoke()

    passed = sum(1 for ok, _, _ in results if ok)
    total = len(results)
    print("\n" + "=" * 60)
    print(f" 결과: {passed}/{total} 통과")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
