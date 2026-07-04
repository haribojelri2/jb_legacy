"""소상공인 상권정보 공공데이터 API 연동 전까지 사용하는 MOCK 상수.

향후 소상공인 상권정보 API(/storeListInRadius 등)로 대체 예정.
매출 이력 데이터는 data/db.py (SQLite) 에서 관리.
"""

# ── 업종·상권 경쟁강도 지수 (0~1, 높을수록 경쟁 심화) ─────────────────────
# 향후: 소상공인 상권정보 API 반경 내 동일 업종 점포 수 기반으로 대체
COMPETITION_INDEX = {
    "lee_sajang":   0.42,   # 한정식, 전주 — 경쟁 보통
    "kim_soojang":  0.35,   # 분식, 부산 해운대 — 경쟁 낮음
    "park_wonjang": 0.78,   # 카페, 강남 — 경쟁 매우 높음
    "choi_daepyo":  0.65,   # 한식뷔페, 수원 — 경쟁 높음
}

# ── 상권 입지 점수 (0~100) ─────────────────────────────────────────────────
# 향후: 통신사 유동인구 데이터 등 고도화 시 대체
LOCATION_SCORE = {
    "lee_sajang":   68,
    "kim_soojang":  72,
    "park_wonjang": 91,
    "choi_daepyo":  63,
}
