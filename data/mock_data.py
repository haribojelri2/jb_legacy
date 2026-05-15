"""데모용 페르소나 데이터."""

USERS = {
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
            "goodwill": 162_000_000,        # 권리금: 450만 × 36개월(30년 A등급)
            "deposit": 100_000_000,         # 보증금
            "equipment_value": 50_000_000,  # 시설·집기
        },
        "personal_assets": {
            "savings": 50_000_000,
            "pension_monthly_expected": 900_000,  # 국민연금 예상 수령액
            "real_estate": 300_000_000,           # 거주용 아파트
        },
        "family": ["lee_gwajang"],
        "total_business_value": 312_000_000,  # 권리금(1억6,200만) + 보증금(1억) + 시설(5,000만)
    },
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
