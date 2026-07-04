"""Youth Matching Agent — 지역 청년 창업가 매칭 & 인수 대출 안내 (DEMO MOCK).

대출 상품은 data/db.py (jb_products 테이블) 에서 관리.
"""

from data.db import fetch_youth_candidates, fetch_loan_products
from data.mock_data import USERS


def get_youth_matching_info(user_id: str) -> dict:
    """매칭 후보 + 대출 상품 + 인수 절차 안내 반환."""
    candidates    = fetch_youth_candidates(user_id, top_n=3)
    loan_products = fetch_loan_products()
    profile       = USERS.get(user_id, {})
    biz           = profile.get("business", {})
    goodwill      = biz.get("goodwill", 0)

    total_new_credit = 0
    for c in candidates:
        # 인수 자금 조달 구조: 자기자본으로 부족한 만큼을 JB 인수 대출로 충당한다.
        # 이 대출액이 곧 JB 신규 여신 고객 창출액 — 청년 매칭의 핵심 사업 가치.
        loan_needed = max(goodwill - c["budget"], 0)             # 대출로 조달할 인수 자금
        loan_ok     = c["loan_eligible"] and loan_needed <= c["loan_limit"]
        c["loan_needed"]     = loan_needed
        c["loan_ok"]         = loan_ok
        c["jb_new_credit"]   = loan_needed if loan_ok else 0      # JB 신규 여신 창출액
        c["can_afford"]      = c["budget"] >= goodwill or loan_ok
        c["total_available"] = c["budget"] + (c["loan_limit"] if c["loan_eligible"] else 0)
        c["funding_gap"]     = 0 if c["can_afford"] else max(goodwill - c["total_available"], 0)
        total_new_credit    += c["jb_new_credit"]

    # UI 표시용 포맷 변환
    formatted_loans = [
        {
            "name":      p["name"],
            "bank":      p["bank"],
            "rate":      f"연 {p['base_rate']}%" if p["base_rate"] else "상담 후 결정",
            "limit":     f"최대 {p['max_amount']:,}원" if p["max_amount"] else "한도 상담",
            "condition": p["target"] or "",
            "feature":   p["notes"] or "",
        }
        for p in loan_products
    ]

    return {
        "candidates":    candidates,
        "loan_products": formatted_loans,
        "goodwill":      goodwill,
        # 매칭된 청년들이 인수 대출로 조달하는 총액 = JB 신규 여신 창출 잠재액
        "jb_new_credit_potential": total_new_credit,
        "transfer_steps": [
            "1. JB Legacy 플랫폼 매칭 후 비공개 인수 의향서 교환",
            "2. JB은행 또는 정부지원 창업자금 사전 승인 (영업일 3~5일)",
            "3. 공인중개사 입회 하 인수인계 계약서 작성",
            "4. 권리금 수취 + 세무사 신고 (기타소득 또는 가업승계 특례 선택)",
            "5. 운영 노하우 전수 기간 (30~90일) — 자문료 협의",
        ],
        "data_source": "DEMO MOCK — 본선 JB Legacy 플랫폼 가입 청년 창업가 DB 자체 운영 예정",
    }
