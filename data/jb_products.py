"""JB금융그룹 상품 카탈로그 — 실존 상품만 수록 (2025년 공시 기준).

수록 원칙: JB금융그룹 실제 계열사(전북은행·광주은행·JB자산운용·JB우리캐피탈)의
실존 상품만 포함한다. JB금융그룹에는 생명보험 계열사가 없으므로 즉시연금/변액연금은
보험이 아니라 전북은행 'JB 리치 100 정기예금 즉시연금형'(매월 원금+이자 분할 지급)으로 제공한다.

출처:
- 전북은행 상품공시 (jbbank.co.kr) — JB 리치 100 정기예금(즉시연금형 실재), JB 1·2·3 정기예금, IRP
- 광주은행 금융상품몰 (kjbank.com)
- 중소벤처기업부·소상공인시장진흥공단 정책자금
"""

JB_PRODUCTS = {

    # ─────────────────────────────────────────────────────
    # 전북은행 — 예금·적금
    # ─────────────────────────────────────────────────────
    "jb_123_deposit": {
        "bank": "전북은행",
        "category": "정기예금",
        "name": "JB 1·2·3 정기예금",
        "base_rate": 2.60,
        "max_rate": 3.10,
        "description": "디지털 전용 정기예금. 비대면 가입 시 우대금리 제공.",
        "term": "1개월 ~ 36개월",
        "min_amount": 1_000_000,
        "tax_benefit": None,
        "target": "일반",
        "notes": "이자지급식·만기일시지급식 선택 가능 / 예금자보호 1억원",
    },
    "jb_rich100_deposit": {
        "bank": "전북은행",
        "category": "정기예금",
        "name": "JB 리치 100 정기예금 (회전형)",
        "base_rate": 2.80,
        "max_rate": 3.35,
        "description": "행복한 노후설계 패키지. 회전형(1~5년)으로 금리 변동 반영. 만 60세 이상 우대금리.",
        "term": "회전형 1~5년",
        "min_amount": 3_000_000,
        "tax_benefit": None,
        "target": "시니어 (만 60세 이상 우대)",
        "notes": "만 60세 이상 우대 / 예금자보호 1억원",
    },
    "jb_rich100_annuity": {
        "bank": "전북은행",
        "category": "즉시연금형예금",
        "name": "JB 리치 100 정기예금 (즉시연금형)",
        "base_rate": 2.80,
        "max_rate": 3.35,
        "description": "목돈 예치 후 매월 원금+이자를 분할 수령하는 시니어 노후설계 예금. 만 60세 이상 우대.",
        "term": "즉시연금형 1~10년",
        "min_amount": 3_000_000,
        "tax_benefit": None,
        "target": "목돈 보유 시니어 (만 60세 이상 우대)",
        "notes": "매월 원금+이자 균등 지급 / 이자분 15.4% 과세 / 예금자보호 1억원 (생명보험 즉시연금과 달리 사업비 없음)",
    },
    "jb_smart_savings": {
        "bank": "전북은행",
        "category": "적금",
        "name": "JB 스마트 자유적금",
        "base_rate": 2.50,
        "max_rate": 3.30,
        "description": "자유납입 적금. 모바일 전용 가입 시 우대.",
        "term": "6개월 ~ 36개월",
        "min_amount": 10_000,
        "tax_benefit": None,
        "target": "일반",
        "notes": "월 최대 100만원 납입",
    },
    "jb_irp": {
        "bank": "전북은행",
        "category": "퇴직연금(IRP)",
        "name": "JB 개인형 퇴직연금(IRP)",
        "base_rate": 3.10,
        "max_rate": 3.10,
        "description": "연간 최대 900만원 세액공제(연금저축 포함). 퇴직금 수령 및 추가 납입 가능.",
        "term": "55세 이후 연금 수령",
        "min_amount": 0,
        "tax_benefit": "세액공제 최대 16.5% (연 148.5만원)",
        "target": "은퇴 준비자",
        "notes": "원리금보장형 편입 시 예금자보호 별도 적용 / 연금 수령 시 연금소득세 3.3~5.5%",
    },
    "jb_pension_savings": {
        "bank": "전북은행",
        "category": "연금저축",
        "name": "JB 연금저축계좌",
        "base_rate": 3.00,
        "max_rate": 3.00,
        "description": "연금저축 세액공제 전용 계좌. IRP와 합산 연 900만원 한도.",
        "term": "5년 이상 유지 후 55세부터 수령",
        "min_amount": 0,
        "tax_benefit": "세액공제 최대 16.5% (연 99만원, 600만원 한도)",
        "target": "은퇴 준비자",
        "notes": "중도해지 시 기타소득세 16.5% 부과",
    },
    "jb_isa": {
        "bank": "전북은행",
        "category": "ISA",
        "name": "JB 개인종합자산관리계좌(ISA)",
        "base_rate": None,
        "max_rate": None,
        "description": "예금·펀드·ETF를 하나의 계좌로 운용. 비과세 혜택 제공.",
        "term": "3년 의무유지",
        "min_amount": 0,
        "tax_benefit": "비과세 한도: 일반형 200만원 / 서민형 400만원",
        "target": "일반·서민",
        "notes": "만기 후 연금계좌 전환 시 전환금액 10% 추가 세액공제",
    },

    # ─────────────────────────────────────────────────────
    # 광주은행 — 예금·적금
    # ─────────────────────────────────────────────────────
    "kj_regular_deposit": {
        "bank": "광주은행",
        "category": "정기예금",
        "name": "KJ 정기예금",
        "base_rate": 2.70,
        "max_rate": 3.70,
        "description": "광주은행 대표 정기예금. 인터넷·스마트뱅킹 가입 시 우대.",
        "term": "1개월 ~ 36개월",
        "min_amount": 1_000_000,
        "tax_benefit": None,
        "target": "일반",
        "notes": "이자지급식 선택 시 매월 이자 수령 가능 / 예금자보호 1억원",
    },
    "kj_prime_age": {
        "bank": "광주은행",
        "category": "정기예금",
        "name": "더 프라임에이지 예금",
        "base_rate": 3.00,
        "max_rate": 3.15,
        "description": "만 50세 이상 전용 시니어 특화 예금.",
        "term": "12개월 ~ 36개월",
        "min_amount": 5_000_000,
        "tax_benefit": None,
        "target": "시니어 (만 50세 이상)",
        "notes": "자동이체 등록 시 우대 / 예금자보호 1억원",
    },
    "kj_select_challenge": {
        "bank": "광주은행",
        "category": "적금",
        "name": "셀렉트챌린지 적금",
        "base_rate": 1.80,
        "max_rate": 4.30,
        "description": "DIY 선택형 적금. 본인이 선택한 미션 달성 시 우대금리.",
        "term": "12개월",
        "min_amount": 10_000,
        "tax_benefit": None,
        "target": "일반",
        "notes": "월 50만원 한도",
    },

    # ─────────────────────────────────────────────────────
    # 전북은행 — 대출 (소상공인)
    # ─────────────────────────────────────────────────────
    "jb_sme_refinance": {
        "bank": "전북은행",
        "category": "대출(소상공인)",
        "name": "소상공인 대환대출",
        "base_rate": 4.50,
        "max_rate": 4.50,
        "description": "고금리 대출을 이용 중인 소상공인 대상 저금리 전환 대출. 최대 10년 장기 분할상환.",
        "term": "최대 10년",
        "min_amount": None,
        "max_amount": None,
        "tax_benefit": None,
        "target": "고금리 대출 이용 소상공인",
        "notes": "전북은행-소상공인시장진흥공단 협약 상품",
    },

    # ─────────────────────────────────────────────────────
    # 광주은행 — 대출 (소상공인)
    # ─────────────────────────────────────────────────────
    "kj_hope_plus": {
        "bank": "광주은행",
        "category": "대출(소상공인)",
        "name": "희망플러스 특례보증대출",
        "base_rate": 1.00,
        "max_rate": None,
        "description": "소상공인 경영 안정 지원 특례보증 대출. 1년차 1% 이내, 이후 CD금리+가산금리.",
        "term": "5년 (1년 거치 + 4년 분할상환)",
        "min_amount": None,
        "max_amount": 20_000_000,
        "tax_benefit": None,
        "target": "소상공인",
        "notes": "1년차 보증료 면제 등 정책 지원",
    },

    # ─────────────────────────────────────────────────────
    # 정부지원 — 청년 창업 (은행 취급)
    # ─────────────────────────────────────────────────────
    "gov_youth_startup": {
        "bank": "중소벤처기업부(소진공)",
        "category": "대출(청년창업)",
        "name": "청년전용창업자금",
        "base_rate": 2.50,
        "max_rate": 2.50,
        "description": "만 39세 이하 청년 창업자 전용 정책자금. 사업체 인수 목적 포함.",
        "term": "시설자금 10년 이내 / 운전자금 5년 이내",
        "min_amount": None,
        "max_amount": 100_000_000,
        "tax_benefit": None,
        "target": "만 39세 이하 창업자 (업력 3년 미만)",
        "notes": "중소벤처기업부 직접대출 또는 은행 대리대출",
    },

}


def get_products_by_category(category: str) -> list[dict]:
    """카테고리별 상품 필터링."""
    return [p for p in JB_PRODUCTS.values() if category in p["category"]]


def get_products_for_retirement(capital: int, risk_profile: str = "conservative") -> list[dict]:
    """은퇴 자산 규모에 맞는 추천 상품 반환 (전부 실존 상품)."""
    all_products = list(JB_PRODUCTS.values())
    categories = ["정기예금", "즉시연금형예금", "퇴직연금", "연금저축"]
    result = [p for p in all_products if any(cat in p["category"] for cat in categories)]
    result = [p for p in result if (p.get("min_amount") or 0) <= capital]
    return result
