"""mock 데이터를 SQLite DB로 초기화하는 스크립트.

실행: python data/init_db.py
DB 파일: data/mock_data.db
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "mock_data.db")

# 데이터 내용이 바뀌면 이 버전을 올린다 → 기존 DB가 있어도 자동 재생성됨
DB_VERSION = "2026-07-04-tx-all-personas-v3"


def get_conn():
    return sqlite3.connect(DB_PATH)


# ── 개인 거래내역 시드 (최근 90일, day_offset 0=오늘) ──────────────────────
# 정상 거래: 주간 시간대, 소액 반복 (월 생활비 약 190만원 수준)
# 이상 거래(is_anomaly=1): 보이스피싱 전형 패턴 — 심야 최초 수취인 고액 이체,
# 상품권 분할 결제, 심야 해외 결제
# city만 바꿔 4개 사장님 페르소나 모두에 동일 구조로 시드한다(거래 안심 데모 일관화).
def _build_transactions(user_id: str, city: str) -> list[tuple]:
    rows = []

    def add(day, time, merchant, category, channel, amount, anomaly=0):
        rows.append((user_id, day, time, merchant, category, channel, amount, anomaly))

    # 월 반복 고정 지출 (자동이체) — 3개월
    for month_start in (2, 32, 62):
        add(month_start,     "09:00", "한국전력/도시가스",   "공과금",  "자동이체", 183_000)
        add(month_start + 1, "09:00", "KT 통신요금",         "통신",    "자동이체",  89_000)
        add(month_start + 3, "09:00", "삼성화재 실손보험",   "보험",    "자동이체", 215_000)

    # 마트·식료품 (주 2~3회, 주간)
    mart_days = [1, 5, 8, 13, 16, 21, 25, 29, 34, 38, 43, 47, 52, 56, 61, 66, 70, 75, 80, 85]
    mart_amounts = [82_000, 64_000, 97_000, 71_000, 88_000, 59_000, 102_000, 76_000,
                    83_000, 69_000, 91_000, 78_000, 86_000, 73_000, 95_000, 67_000,
                    84_000, 72_000, 89_000, 61_000]
    for d, amt in zip(mart_days, mart_amounts):
        add(d, "11:20", f"하나로마트 {city}점", "식료품", "카드", amt)

    # 병원·약국 (월 2~3회)
    for d, m, amt in [(6, f"{city} 내과의원", 74_000), (7, "온누리약국", 28_000),
                      (20, f"{city} 내과의원", 68_000), (36, f"{city} 내과의원", 81_000),
                      (37, "온누리약국", 31_000), (55, f"{city} 정형외과", 125_000),
                      (56, "온누리약국", 24_000), (78, f"{city} 내과의원", 71_000)]:
        add(d, "10:40", m, "병원·약국", "카드", amt)

    # 외식·경조사·교통 등
    for d, t, m, c, amt in [(10, "18:30", f"{city} 맛집골목", "외식", 48_000),
                            (24, "12:10", "가족 외식 (백반집)", "외식", 56_000),
                            (40, "18:50", f"{city} 맛집골목", "외식", 43_000),
                            (68, "12:30", "가족 외식 (백반집)", "외식", 61_000),
                            (15, "14:00", "친지 경조사비", "경조사", 100_000),
                            (49, "14:00", "지인 경조사비", "경조사", 100_000),
                            (11, "09:30", f"{city} 주유소", "교통", 70_000),
                            (44, "09:40", f"{city} 주유소", "교통", 72_000),
                            (77, "09:20", f"{city} 주유소", "교통", 68_000)]:
        add(d, t, m, c, "카드", amt)

    # ── 이상 거래 (보이스피싱 패턴, ground-truth 라벨) ──
    add(3,  "02:17", "미상 개인계좌 이체 (최초 수취인)", "이체",   "이체", 8_000_000, 1)
    add(3,  "02:31", "ABC상품권몰",                      "상품권", "카드", 1_990_000, 1)
    add(3,  "02:38", "ABC상품권몰",                      "상품권", "카드", 1_990_000, 1)
    add(12, "04:05", "해외 온라인 결제 (QX-MALL)",       "해외",   "카드", 1_450_000, 1)

    return rows


# 사장님 페르소나별 (user_id, 거래 지역) — mock_data.USERS와 일치
_TX_PERSONAS = [
    ("lee_sajang",   "전주"),
    ("kim_soojang",  "부산"),
    ("park_wonjang", "강남"),
    ("choi_daepyo",  "수원"),
]


def seed_transactions(cur):
    """transactions 테이블이 비어 있을 때만 시드 (idempotent)."""
    count = cur.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    if count:
        return
    rows = []
    for uid, city in _TX_PERSONAS:
        rows += _build_transactions(uid, city)
    cur.executemany(
        "INSERT INTO transactions "
        "(user_id, day_offset, tx_time, merchant, category, channel, amount, is_anomaly) "
        "VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # ── 테이블 생성 ────────────────────────────────────────────────────────
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS revenue_history (
        user_id      TEXT NOT NULL,
        month_offset INTEGER NOT NULL,
        revenue_10k  INTEGER NOT NULL,
        PRIMARY KEY (user_id, month_offset)
    );

    CREATE TABLE IF NOT EXISTS youth_candidates (
        id            TEXT PRIMARY KEY,
        name          TEXT NOT NULL,
        age           INTEGER NOT NULL,
        region        TEXT NOT NULL,
        budget        INTEGER NOT NULL,
        loan_eligible INTEGER NOT NULL,
        loan_limit    INTEGER NOT NULL,
        rating        REAL NOT NULL,
        intro         TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS youth_preferred_types (
        youth_id  TEXT NOT NULL,
        type_name TEXT NOT NULL,
        PRIMARY KEY (youth_id, type_name)
    );

    CREATE TABLE IF NOT EXISTS user_type_mapping (
        user_id   TEXT NOT NULL,
        type_name TEXT NOT NULL,
        PRIMARY KEY (user_id, type_name)
    );

    CREATE TABLE IF NOT EXISTS user_region_mapping (
        user_id TEXT PRIMARY KEY,
        region  TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     TEXT NOT NULL,
        day_offset  INTEGER NOT NULL,
        tx_time     TEXT NOT NULL,
        merchant    TEXT NOT NULL,
        category    TEXT NOT NULL,
        channel     TEXT NOT NULL,
        amount      INTEGER NOT NULL,
        is_anomaly  INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS jb_products (
        product_id      TEXT PRIMARY KEY,
        bank            TEXT NOT NULL,
        category        TEXT NOT NULL,
        name            TEXT NOT NULL,
        base_rate       REAL,
        max_rate        REAL,
        expected_return REAL,
        description     TEXT,
        term            TEXT,
        min_amount      INTEGER,
        max_amount      INTEGER,
        tax_benefit     TEXT,
        target          TEXT,
        notes           TEXT
    );
    """)

    # ── 매출 이력 ──────────────────────────────────────────────────────────
    revenue_data = {
        "lee_sajang": [
            1200, 1180, 1210, 1190, 1170, 1200,
            1220, 1250, 1230, 1260, 1240, 1270,
            1290, 1310, 1300, 1320, 1330, 1350,
            1380, 1400, 1390, 1420, 1410, 1440,
        ],
        "kim_soojang": [
            510, 520, 505, 515, 508, 512,
            498, 495, 502, 488, 493, 480,
            472, 478, 465, 470, 460, 455,
            448, 452, 440, 445, 438, 430,
        ],
        "park_wonjang": [
            870, 860, 880, 850, 840, 855,
            820, 815, 830, 800, 810, 790,
            760, 770, 750, 740, 755, 730,
            710, 720, 700, 695, 705, 680,
        ],
        "choi_daepyo": [
            2300, 2250, 2350, 2280, 2200, 2320,
            2500, 2480, 2520, 2460, 2550, 2480,
            2700, 2680, 2720, 2660, 2710, 2680,
            2850, 2830, 2870, 2810, 2860, 2840,
        ],
    }
    cur.executemany(
        "INSERT OR REPLACE INTO revenue_history VALUES (?,?,?)",
        [(uid, i, rev) for uid, revs in revenue_data.items() for i, rev in enumerate(revs)],
    )

    # ── 개인 거래내역 (이상거래 탐지·소비흐름 분석용) ───────────────────────
    seed_transactions(cur)

    # ── 청년 후보 (개인정보 보호: 계약 전 단계라 익명 프로필로 표시) ──────────
    # 실존 인물이 아니며, 매칭 서비스 특성상 성만 공개하고 이름은 마스킹한다.
    candidates = [
        ("youth_001", "정OO", 28, "전주",  80_000_000, 1, 150_000_000, 4.7,
         "전통 한식을 현대적으로 재해석하고 싶습니다. 요리 경력 4년, 소믈리에 자격증 보유."),
        ("youth_002", "이OO", 31, "전주",  60_000_000, 1, 120_000_000, 4.5,
         "전주 한옥마을 문화관광 콘텐츠와 연계한 한정식 운영 계획. 관광경영 석사 졸업."),
        ("youth_003", "김OO", 26, "부산",  40_000_000, 1,  80_000_000, 4.2,
         "부산 해운대 관광객 타겟 프리미엄 분식집 창업 희망. SNS 마케팅 전문."),
        ("youth_004", "박OO", 29, "강남", 200_000_000, 1, 300_000_000, 4.9,
         "스페셜티 커피 바리스타 대회 입상. 강남 특화 브런치 카페 운영 희망."),
        ("youth_005", "최OO", 33, "수원", 100_000_000, 1, 200_000_000, 4.4,
         "외식업 컨설팅 5년 경력. 뷔페 운영 시스템 개선 및 원가 절감 전문."),
        ("youth_006", "윤OO", 27, "강남", 150_000_000, 1, 250_000_000, 4.6,
         "제과제빵 전문과정 수료. 디저트 카페 운영 희망, SNS 마케팅 보유."),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO youth_candidates VALUES (?,?,?,?,?,?,?,?,?)", candidates
    )

    preferred_types = [
        ("youth_001", "한식"), ("youth_001", "한정식"), ("youth_001", "전통음식"),
        ("youth_002", "한식"), ("youth_002", "한정식"), ("youth_002", "카페"),
        ("youth_003", "분식"), ("youth_003", "한식"),   ("youth_003", "간편식"),
        ("youth_004", "카페"), ("youth_004", "베이커리"), ("youth_004", "음료"),
        ("youth_005", "한식"), ("youth_005", "뷔페"),   ("youth_005", "단체급식"),
        ("youth_006", "카페"), ("youth_006", "디저트"), ("youth_006", "음료"),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO youth_preferred_types VALUES (?,?)", preferred_types
    )

    user_types = [
        ("lee_sajang",   "한식"), ("lee_sajang",   "한정식"), ("lee_sajang",   "전통음식"),
        ("kim_soojang",  "분식"), ("kim_soojang",  "한식"),   ("kim_soojang",  "간편식"),
        ("park_wonjang", "카페"), ("park_wonjang", "음료"),   ("park_wonjang", "베이커리"),
        ("park_wonjang", "디저트"),
        ("choi_daepyo",  "한식"), ("choi_daepyo",  "뷔페"),   ("choi_daepyo",  "단체급식"),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO user_type_mapping VALUES (?,?)", user_types
    )

    user_regions = [
        ("lee_sajang",  "전주"),
        ("kim_soojang", "부산"),
        ("park_wonjang","강남"),
        ("choi_daepyo", "수원"),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO user_region_mapping VALUES (?,?)", user_regions
    )

    # ── JB 금융상품 ────────────────────────────────────────────────────────
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from data.jb_products import JB_PRODUCTS
    products = [
        (
            pid,
            p["bank"], p["category"], p["name"],
            p.get("base_rate"), p.get("max_rate"), p.get("expected_return"),
            p.get("description"), p.get("term"),
            p.get("min_amount"), p.get("max_amount"),
            p.get("tax_benefit"), p.get("target"), p.get("notes"),
        )
        for pid, p in JB_PRODUCTS.items()
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO jb_products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        products,
    )

    # 데이터 버전 기록 (재생성 트리거용)
    cur.execute("CREATE TABLE IF NOT EXISTS _meta (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("INSERT OR REPLACE INTO _meta VALUES ('version', ?)", (DB_VERSION,))

    conn.commit()
    conn.close()
    print(f"[init_db] mock_data.db 초기화 완료 (v={DB_VERSION}) → {DB_PATH}")


if __name__ == "__main__":
    init_db()
