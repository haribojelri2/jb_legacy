"""JB금융그룹 상품 카탈로그 (2025년 공시 기준).

출처:
- 전북은행 상품 페이지 (jbbank.co.kr)
- 광주은행 금융상품몰 (kjbank.com) — 79개 상품 운영
- JB자산운용 운용정보 (jbam.co.kr)
- 금융감독원 금융상품통합비교공시 (finlife.fss.or.kr)
- 생명보험협회 공시이율 (2025년 평균)
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
        "notes": "특별금리 이벤트 기간 중 최고 연 3.10%",
    },
    "jb_rich100_deposit": {
        "bank": "전북은행",
        "category": "정기예금",
        "name": "JB 리치 100 정기예금",
        "base_rate": 2.80,
        "max_rate": 3.35,
        "description": "회전형·즉시연금형 선택 가능. 만 60세 이상 추가 우대금리 0.55%.",
        "term": "회전형 1~5년 / 즉시연금형 1~10년",
        "min_amount": 3_000_000,
        "tax_benefit": None,
        "target": "시니어 (만 60세 이상 우대)",
        "notes": "즉시연금형: 매월 원금+이자 분할 지급 / 예금자보호 1억원",
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
        "notes": "원리금보장형 편입 시 예금자보호 별도 적용",
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
        "notes": "79개 운영 상품 중 핵심 상품",
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
        "notes": "영업점 전용 상품 / 자동이체 등록 시 우대",
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
    "kj_youth_saving": {
        "bank": "광주은행",
        "category": "적금",
        "name": "전남청년미래적금",
        "base_rate": 3.00,
        "max_rate": 4.50,
        "description": "전라남도 청년 대상 고금리 적금.",
        "term": "24개월",
        "min_amount": 10_000,
        "tax_benefit": None,
        "target": "청년 (만 19~34세)",
        "notes": "전라남도 거주 청년 한정",
    },

    # ─────────────────────────────────────────────────────
    # JB자산운용 — 펀드
    # ─────────────────────────────────────────────────────
    "jbam_monthly_dividend": {
        "bank": "JB자산운용",
        "category": "펀드(월배당)",
        "name": "JB 월배당 혼합채권형 펀드",
        "base_rate": None,
        "max_rate": None,
        "expected_return": 4.50,
        "description": "채권 60% 이상 + 주식 혼합. 매월 분배금 지급.",
        "term": "환매 수수료 없음 (90일 이후)",
        "min_amount": 1_000_000,
        "tax_benefit": None,
        "target": "은퇴 후 월소득 필요자",
        "notes": "예상 연 분배율 4.5% / 원금 손실 가능 / 위험등급 3등급(중간)",
    },
    "jbam_bond_fund": {
        "bank": "JB자산운용",
        "category": "펀드(채권형)",
        "name": "JB 채권형 펀드",
        "base_rate": None,
        "max_rate": None,
        "expected_return": 3.80,
        "description": "국공채·우량회사채 60% 이상 투자. 안정 수익 추구.",
        "term": "환매 수수료 없음",
        "min_amount": 1_000_000,
        "tax_benefit": None,
        "target": "안전 추구 투자자",
        "notes": "예상 연 수익률 3.8% / 위험등급 4등급(저위험)",
    },
    "jbam_mixed_fund": {
        "bank": "JB자산운용",
        "category": "펀드(혼합형)",
        "name": "JB 성장혼합형 펀드",
        "base_rate": None,
        "max_rate": None,
        "expected_return": 6.00,
        "description": "주식·채권 균형 배분. 중장기 자본성장 추구.",
        "term": "환매 수수료 없음 (90일 이후)",
        "min_amount": 1_000_000,
        "tax_benefit": None,
        "target": "중위험 수용 투자자",
        "notes": "예상 연 수익률 6.0% / 위험등급 2등급(다소 높은 위험)",
    },
    "jbam_realestate_fund": {
        "bank": "JB자산운용",
        "category": "펀드(부동산)",
        "name": "JB 부동산 실물 펀드",
        "base_rate": None,
        "max_rate": None,
        "expected_return": 5.50,
        "description": "국내외 상업용 부동산 매입·임대 수익. Buy & Lease 방식.",
        "term": "3년 폐쇄형",
        "min_amount": 10_000_000,
        "tax_benefit": None,
        "target": "고액 자산가",
        "notes": "비유동성 위험 / 위험등급 2등급 / 사모펀드 성격",
    },

    # ─────────────────────────────────────────────────────
    # 생명보험 연계 (JB생명 공시이율 기준)
    # ─────────────────────────────────────────────────────
    "jb_immediate_annuity": {
        "bank": "JB생명",
        "category": "즉시연금",
        "name": "JB 즉시연금보험",
        "base_rate": 2.31,
        "max_rate": 2.45,
        "description": "목돈 납입 즉시 다음달부터 연금 수령. 종신 또는 확정기간 선택.",
        "term": "종신형 또는 10·20년 확정형",
        "min_amount": 30_000_000,
        "tax_benefit": None,
        "target": "목돈 보유 시니어",
        "notes": "공시이율 2025년 평균 2.31~2.45% / 사업비 차감 후 실질 수령액 확인 필요",
    },
    "jb_variable_annuity": {
        "bank": "JB생명",
        "category": "변액연금",
        "name": "JB 변액연금보험 (최저보증형)",
        "base_rate": None,
        "max_rate": None,
        "guaranteed_return": 5.00,
        "description": "펀드 운용 수익과 연 단리 5% 보증 중 높은 금액으로 연금 지급.",
        "term": "10년 이상 납입 후 연금 전환",
        "min_amount": 300_000,
        "tax_benefit": "10년 유지 시 보험차익 비과세",
        "target": "장기 은퇴 준비자",
        "notes": "최저연금보증 연 단리 5% / 펀드 손실 시에도 보증금액 수령 / 위험등급 2등급",
    },

    # ─────────────────────────────────────────────────────
    # 전북은행 — 대출 (소상공인)
    # 출처: jbbank.co.kr / 소상공인시장진흥공단 협약
    # ─────────────────────────────────────────────────────
    "jb_sme_refinance": {
        "bank": "전북은행",
        "category": "대출(소상공인)",
        "name": "소상공인 대환대출",
        "base_rate": 4.50,
        "max_rate": 4.50,
        "description": "연 7% 이상 고금리 대출을 이용 중인 소상공인 대상 저금리 전환 대출. 최대 10년 장기 분할상환.",
        "term": "최대 10년",
        "min_amount": None,
        "max_amount": None,
        "tax_benefit": None,
        "target": "고금리 대출 이용 소상공인",
        "notes": "전북은행-소상공인시장진흥공단 협약 상품 / 전북은행 취급금액 1위",
    },

    # ─────────────────────────────────────────────────────
    # 광주은행 — 대출 (소상공인)
    # 출처: kjbank.com
    # ─────────────────────────────────────────────────────
    "kj_hope_plus": {
        "bank": "광주은행",
        "category": "대출(소상공인)",
        "name": "희망플러스 특례보증대출",
        "base_rate": 1.00,
        "max_rate": None,
        "description": "소상공인 경영 안정 지원 특례보증 대출. 1년차 1% 이내, 이후 CD금리+1.7%p 이내.",
        "term": "5년 (1년 거치 + 4년 분할상환)",
        "min_amount": None,
        "max_amount": 20_000_000,
        "tax_benefit": None,
        "target": "소상공인",
        "notes": "1년차 보증료 전액 면제 / 2~5년차 보증료 0.2%p 감면 (0.8%→0.6%)",
    },

    # ─────────────────────────────────────────────────────
    # 정부지원 — 청년 창업 (은행 취급)
    # 출처: 중소벤처기업부 / 소상공인시장진흥공단
    # ─────────────────────────────────────────────────────
    "gov_youth_startup": {
        "bank": "정부지원(중소벤처기업부)",
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
        "notes": "제조업·지역특화산업 최대 2억원 / 중소벤처기업부 직접대출 또는 은행 대리대출",
    },

}


def get_products_by_category(category: str) -> list[dict]:
    """카테고리별 상품 필터링."""
    return [p for p in JB_PRODUCTS.values() if category in p["category"]]


def get_products_for_retirement(capital: int, risk_profile: str = "conservative") -> list[dict]:
    """은퇴 자산 규모와 리스크 성향에 맞는 추천 상품 반환."""
    all_products = list(JB_PRODUCTS.values())

    if risk_profile == "conservative":
        # 안전 중심: 예금, IRP, 즉시연금
        categories = ["정기예금", "퇴직연금", "연금저축", "즉시연금"]
    elif risk_profile == "moderate":
        # 균형: 예금 + 채권펀드 + 월배당
        categories = ["정기예금", "펀드(월배당)", "펀드(채권형)", "퇴직연금"]
    else:  # aggressive
        categories = ["펀드(혼합형)", "펀드(부동산)", "펀드(월배당)", "변액연금"]

    result = [p for p in all_products if any(cat in p["category"] for cat in categories)]

    # 최소 가입금액 필터
    result = [p for p in result if (p.get("min_amount") or 0) <= capital]

    return result
