"""tests/test_pdf.py — PDF 리포트 생성 및 검증 테스트."""

import os
import sys

# 프로젝트 루트를 import 경로에 추가
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest
from tools.pdf_report import build_pdf_report
from data.mock_data import USERS

def test_build_pdf_report_success():
    """대표 페르소나(이사장) 데이터를 기반으로 PDF 리포트가 정상 생성되는지 검증."""
    # 1. Mock 데이터 준비
    profile = USERS["lee_sajang"]
    life_inputs = {
        "succession": "예",
        "market_trend": "보합",
        "retirement_timeline": "3년 이내",
        "target_monthly": 3_000_000,
        "home_pension": "아니오",
        "monthly_profit": 4_500_000,
    }
    
    # graph 실행 시뮬레이션 결과 구조
    result = {
        "user_profile": profile,
        "query": "폐업할지 승계할지 고민입니다.",
        "recommended_scenario": "C",
        "tax_comparison": {
            "sale": {
                "total_tax": 28_754_000,
            },
            "special": {
                "label": "가업승계 과세특례",
                "total_tax": 0,
                "note": "조세특례제한법 제30조의6"
            }
        },
        "business_valuation": {
            "components": {
                "권리금": 162_000_000,
                "보증금": 100_000_000,
                "시설": 50_000_000,
            }
        },
        "retirement_portfolio": {
            "scenario_sale": {
                "total_capital": 333_000_000,
                "monthly_income": {"합계": 2_880_000},
                "surplus_monthly": -120_000,
            },
            "scenario_succession": {
                "total_capital": 150_000_000,
                "monthly_income": {"합계": 2_890_000},
                "surplus_monthly": -110_000,
            },
            "scenario_hybrid": {
                "total_capital": 241_500_000,
                "monthly_income": {"합계": 2_820_000},
                "surplus_monthly": -180_000,
            },
            "monte_carlo_comparison": {
                "A안": {
                    "survival_curve": {60: 100, 70: 80, 80: 50, 90: 30, 100: 37},
                },
                "B안": {
                    "survival_curve": {60: 100, 70: 90, 80: 40, 90: 20, 100: 16},
                },
                "C안": {
                    "survival_curve": {60: 100, 70: 85, 80: 45, 90: 25, 100: 22},
                },
                "_model": {
                    "description": "의료비 쇼크 복합 포아송 과정 시뮬레이션"
                }
            }
        },
        "final_response": "종합 의견: 개인의 안정과 가족 자산 보존을 위해 C안(절충안)을 권장합니다.",
        "final_response_raw": "종합 의견: 개인의 안정과 가족 자산 보존을 위해 C안(절충안)을 권장합니다.",
    }

    # 2. PDF 생성 호출
    pdf_bytes = build_pdf_report(result, life_inputs, profile)
    
    # 3. PDF 포맷 기본 검증
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000  # 최소 1KB 이상
    assert pdf_bytes.startswith(b"%PDF-")  # PDF 헤더 매직 넘버 검증
    assert b"EOF" in pdf_bytes  # PDF 종료 바이트 검증

    # 4. 파일 저장 및 디렉토리 확인 (수동 확인용 미리보기)
    output_dir = os.path.join(_ROOT, "tests")
    output_path = os.path.join(output_dir, "test_report_preview.pdf")
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
        
    assert os.path.exists(output_path)
    print(f"\n[PASS] PDF Report successfully generated at: {output_path}")

if __name__ == "__main__":
    test_build_pdf_report_success()
