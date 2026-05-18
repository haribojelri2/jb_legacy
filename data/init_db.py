"""mock 데이터를 SQLite DB로 초기화하는 스크립트.

실행: python data/init_db.py
DB 파일: data/mock_data.db
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "mock_data.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


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

    # ── 청년 후보 ──────────────────────────────────────────────────────────
    candidates = [
        ("youth_001", "정민준", 28, "전주",  80_000_000, 1, 150_000_000, 4.7,
         "전통 한식을 현대적으로 재해석하고 싶습니다. 요리 경력 4년, 소믈리에 자격증 보유."),
        ("youth_002", "이수아", 31, "전주",  60_000_000, 1, 120_000_000, 4.5,
         "전주 한옥마을 문화관광 콘텐츠와 연계한 한정식 운영 계획. 관광경영 석사 졸업."),
        ("youth_003", "김태양", 26, "부산",  40_000_000, 1,  80_000_000, 4.2,
         "부산 해운대 관광객 타겟 프리미엄 분식집 창업 희망. SNS 마케팅 전문."),
        ("youth_004", "박하은", 29, "강남", 200_000_000, 1, 300_000_000, 4.9,
         "스페셜티 커피 바리스타 세계대회 입상. 강남 특화 브런치 카페 운영 희망."),
        ("youth_005", "최준혁", 33, "수원", 100_000_000, 1, 200_000_000, 4.4,
         "외식업 컨설팅 5년 경력. 뷔페 운영 시스템 개선 및 원가 절감 전문."),
        ("youth_006", "윤서연", 27, "강남", 150_000_000, 1, 250_000_000, 4.6,
         "파리 르 코르동 블뢰 파티시에 과정 수료. 인스타그램 팔로워 8만명 보유."),
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

    conn.commit()
    conn.close()
    print(f"[init_db] mock_data.db 초기화 완료 → {DB_PATH}")


if __name__ == "__main__":
    init_db()
