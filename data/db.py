"""SQLite mock DB 접근 모듈. 앱 시작 시 DB가 없으면 자동 초기화."""

import os
import sqlite3
import math

DB_PATH = os.path.join(os.path.dirname(__file__), "mock_data.db")


def _ensure_db():
    if not os.path.exists(DB_PATH):
        from data.init_db import init_db
        init_db()


def get_conn() -> sqlite3.Connection:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── 매출 이력 ──────────────────────────────────────────────────────────────

def fetch_revenue_history(user_id: str) -> list[int]:
    """24개월 매출 이력 반환 (최근 → 과거 순, 만원 단위)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT revenue_10k FROM revenue_history "
            "WHERE user_id=? ORDER BY month_offset ASC",
            (user_id,),
        ).fetchall()
    return [r["revenue_10k"] for r in rows]




# ── 청년 후보 매칭 ──────────────────────────────────────────────────────────

def fetch_youth_candidates(user_id: str, top_n: int = 3) -> list[dict]:
    """user_id 업종·지역에 맞는 청년 후보 상위 N명 반환."""
    with get_conn() as conn:
        # 사용자 업종·지역
        user_types = {
            r["type_name"]
            for r in conn.execute(
                "SELECT type_name FROM user_type_mapping WHERE user_id=?", (user_id,)
            ).fetchall()
        }
        region_row = conn.execute(
            "SELECT region FROM user_region_mapping WHERE user_id=?", (user_id,)
        ).fetchone()
        user_region = region_row["region"] if region_row else ""

        # 전체 후보
        candidates = conn.execute("SELECT * FROM youth_candidates").fetchall()
        result = []
        for c in candidates:
            c_types = {
                r["type_name"]
                for r in conn.execute(
                    "SELECT type_name FROM youth_preferred_types WHERE youth_id=?",
                    (c["id"],),
                ).fetchall()
            }
            overlap       = len(c_types & user_types)
            region_match  = 1 if c["region"] == user_region else 0
            if overlap == 0 and region_match == 0:
                continue
            score = overlap * 2 + region_match + c["rating"] * 0.5
            result.append({
                "id":            c["id"],
                "name":          c["name"],
                "age":           c["age"],
                "region":        c["region"],
                "budget":        c["budget"],
                "loan_eligible": bool(c["loan_eligible"]),
                "loan_limit":    c["loan_limit"],
                "rating":        c["rating"],
                "intro":         c["intro"],
                "_match_score":  round(score, 2),
            })

    result.sort(key=lambda x: x["_match_score"], reverse=True)
    return result[:top_n]


# ── JB 금융상품 조회 ────────────────────────────────────────────────────────

def fetch_products_by_category(category: str) -> list[dict]:
    """카테고리로 상품 조회 (부분 일치)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jb_products WHERE category LIKE ?", (f"%{category}%",)
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_loan_products() -> list[dict]:
    """대출 상품 전체 조회."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jb_products WHERE category LIKE '대출%'"
        ).fetchall()
    return [dict(r) for r in rows]


# ── 매출 추세 계산 (mock_mydata.calc_revenue_trend 대체) ────────────────────

def calc_revenue_trend(user_id: str) -> dict:
    history = fetch_revenue_history(user_id)
    if not history:
        return {}

    recent_6  = sum(history[:6])  / 6
    prev_6    = sum(history[6:12]) / 6
    recent_12 = sum(history[:12]) / 12
    prev_12   = sum(history[12:24]) / 12

    mom_change = (history[0] - history[1]) / history[1] if history[1] else 0
    yoy_change = (recent_12 - prev_12) / prev_12 if prev_12 else 0

    mean_r   = recent_6
    variance = sum((x - mean_r) ** 2 for x in history[:6]) / 6
    volatility = math.sqrt(variance) / mean_r if mean_r else 0

    return {
        "recent_6m_avg":   int(recent_6 * 10_000),
        "prev_6m_avg":     int(prev_6 * 10_000),
        "mom_change_pct":  round(mom_change * 100, 1),
        "yoy_change_pct":  round(yoy_change * 100, 1),
        "volatility":      round(volatility, 3),
        "history_10k":     history,
        "trend_direction": "성장" if yoy_change > 0.03 else ("하락" if yoy_change < -0.03 else "보합"),
    }
