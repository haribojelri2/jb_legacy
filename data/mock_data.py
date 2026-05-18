"""데모용 페르소나 데이터."""

USERS = {
    # ── 사장님 페르소나 ──────────────────────────────────────────
    "lee_sajang": {
        "name": "이사장",
        "age": 62,
        "location": "전북 전주",
        "type": "self_employed",
        "slow_ui": True,
        "business": {
            "name": "이씨 한정식",
            "type": "음식업",
            "years_operating": 30,
            "monthly_revenue": 12_000_000,
            "monthly_cost": 7_500_000,
            "monthly_profit": 4_500_000,
            "goodwill": 162_000_000,        # 450만 × 36개월 (30년 A등급)
            "deposit": 100_000_000,
            "equipment_value": 50_000_000,
        },
        "personal_assets": {
            "savings": 50_000_000,
            "pension_monthly_expected": 900_000,
            "real_estate": 300_000_000,
        },
        "family": ["lee_gwajang"],
        "total_business_value": 312_000_000,
    },

    "kim_soojang": {
        "name": "김소장",
        "age": 58,
        "location": "부산 해운대",
        "type": "self_employed",
        "slow_ui": False,
        "business": {
            "name": "김씨 분식",
            "type": "음식업",
            "years_operating": 5,
            "monthly_revenue": 5_000_000,
            "monthly_cost": 3_000_000,
            "monthly_profit": 2_000_000,
            "goodwill": 48_000_000,         # 200만 × 24개월 (5년 C등급)
            "deposit": 30_000_000,
            "equipment_value": 10_000_000,
        },
        "personal_assets": {
            "savings": 20_000_000,
            "pension_monthly_expected": 500_000,
            "real_estate": 150_000_000,
        },
        "family": [],
        "total_business_value": 88_000_000,
        # 매각세금 약 230만 / 승계세금 0 → 규모 작아 둘 다 세금 미미
    },

    "park_wonjang": {
        "name": "박원장",
        "age": 55,
        "location": "서울 강남",
        "type": "self_employed",
        "slow_ui": False,
        "business": {
            "name": "박씨 카페",
            "type": "음식업",
            "years_operating": 8,
            "monthly_revenue": 8_000_000,
            "monthly_cost": 5_000_000,
            "monthly_profit": 3_000_000,
            "goodwill": 72_000_000,         # 300만 × 24개월 (8년 C등급)
            "deposit": 1_000_000_000,       # 강남 상가 보증금 10억
            "equipment_value": 50_000_000,
        },
        "personal_assets": {
            "savings": 100_000_000,
            "pension_monthly_expected": 600_000,
            "real_estate": 800_000_000,
        },
        "family": [],
        "total_business_value": 1_122_000_000,
        # 매각세금 약 1,077만 / 승계세금 약 1,342만 → 외부 매각이 유리한 드문 케이스
    },

    "choi_daepyo": {
        "name": "최대표",
        "age": 65,
        "location": "경기 수원",
        "type": "self_employed",
        "slow_ui": False,
        "business": {
            "name": "최씨 한식뷔페",
            "type": "음식업",
            "years_operating": 22,
            "monthly_revenue": 25_000_000,
            "monthly_cost": 15_000_000,
            "monthly_profit": 10_000_000,
            "goodwill": 360_000_000,        # 1,000만 × 36개월 (22년 A등급)
            "deposit": 500_000_000,
            "equipment_value": 150_000_000,
        },
        "personal_assets": {
            "savings": 200_000_000,
            "pension_monthly_expected": 1_200_000,
            "real_estate": 600_000_000,
        },
        "family": [],
        "total_business_value": 1_010_000_000,
        # 매각세금 약 8,842만 / 승계세금 약 110만 → 승계 압도적 유리
    },

    # ── 자녀 페르소나 ────────────────────────────────────────────
    "lee_gwajang": {
        "name": "이과장",
        "age": 32,
        "location": "서울",
        "type": "child",
        "parent": "lee_sajang",
        "job": "서울 직장인",
        "slow_ui": False,
    },
}
