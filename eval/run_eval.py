"""회귀 평가 하네스 — 데모 질의를 그래프에 태우고 GAN 채점으로 품질 회귀 감지.

사용:
    python -m eval.run_eval            # 실행 후 eval/results/ 에 결과 저장
    python -m eval.run_eval --gate 70  # 총점 평균이 70 미만이면 exit 1 (CI 게이트)

OPENAI_API_KEY / ANTHROPIC_API_KEY 가 필요하다 (실제 LLM 호출).
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from graph import run_query
from agents.gan_tester import GANTester

# 데모 시나리오 golden query set
_QUERIES = [
    ("lee_sajang", "폐업할지 승계할지 고민입니다. 세금이랑 노후 생활비까지 분석해주세요."),
    ("lee_sajang", "가업승계하면 증여세가 얼마나 나오나요?"),
    ("lee_sajang", "가게 팔면 노후 생활비로 매달 얼마나 받을 수 있나요?"),
    ("lee_sajang", "권리금 시세가 얼마나 되나요?"),
]

_RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", type=float, default=None,
                    help="평균 총점이 이 값 미만이면 exit 1 (CI 회귀 게이트)")
    ap.add_argument("--label", default="run", help="결과 파일 라벨")
    args = ap.parse_args()

    tester = GANTester(rounds=1)
    rows, scores = [], []
    for user_id, query in _QUERIES:
        state = run_query(user_id=user_id, query=query)
        resp = state.get("final_response", "")
        report = tester.run(query=query, ai_response=resp)
        fs = report.final_score
        scores.append(fs.total_score)
        rows.append({
            "user_id": user_id,
            "query": query,
            "total_score": fs.total_score,
            "verdict": fs.verdict,
            "category_scores": {s.category: s.score for s in fs.scores},
            "compliance_passed": state.get("compliance_passed"),
            "response_len": len(resp),
        })
        print(f"[{fs.total_score:3d}점 / {fs.verdict}] {query[:40]}")

    avg = sum(scores) / len(scores) if scores else 0
    summary = {"label": args.label, "avg_score": round(avg, 1), "count": len(rows), "rows": rows}

    os.makedirs(_RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(_RESULTS_DIR, f"{args.label}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n평균 총점: {avg:.1f}  ({len(rows)}개 질의)")
    print(f"결과 저장: {out_path}")

    if args.gate is not None and avg < args.gate:
        print(f"회귀 게이트 실패: 평균 {avg:.1f} < 기준 {args.gate}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
