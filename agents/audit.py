"""금융 감사 추적(Audit Trail) — 분석 1건마다 근거·검증 이력을 DB에 자동 적재.

규제·감사(Compliance Auditing) 대응을 위해 "어떤 질문에, 어떤 모델이, 어떤 RAG 근거로,
컴플라이언스·GAN 검증 몇 점을 받아, 어떤 최종안이 나왔는지"를 jb_legacy_memory.db의
audit_trail 테이블에 기록한다. 에이전트가 스스로 자신의 판단 이력을 남겨 휘발을 막는다.
"""

import hashlib
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "jb_legacy_memory.db")
_KST = timezone(timedelta(hours=9))

_COLS = ["ts", "user_id", "question_hash", "query_preview", "models", "rag_sources",
         "compliance", "gan_verdict", "gan_score", "final_scenario"]


def init_audit_table() -> None:
    with sqlite3.connect(_DB) as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS audit_trail ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, user_id TEXT, thread_id TEXT, "
            "question_hash TEXT, query_preview TEXT, models TEXT, rag_sources TEXT, "
            "compliance TEXT, gan_verdict TEXT, gan_score INTEGER, final_scenario TEXT)"
        )


def _rag_sources(rag_context: str) -> str:
    if not rag_context:
        return ""
    labels = re.findall(r"\[출처\s*\d+[^\]]*\]", rag_context)
    return " ".join(dict.fromkeys(labels)) or f"세법 근거 {len(rag_context)}자"


def log_audit(user_id: str, query: str, state: dict, thread_id: str = "") -> None:
    """분석 최종 상태에서 감사 레코드 1건 적재. 로깅 실패가 분석을 막지 않도록 방어."""
    try:
        init_audit_table()
        from agents.llm import _configured_models
        rec = (
            datetime.now(_KST).isoformat(timespec="seconds"),
            user_id,
            thread_id or user_id,
            hashlib.sha256((query or "").encode("utf-8")).hexdigest()[:16],
            (query or "")[:80],
            ",".join(_configured_models()),
            _rag_sources(state.get("tax_rag_context", "")),
            (state.get("compliance_feedback", "") or "")[:120],
            state.get("gan_verdict", "") or "",
            int(state.get("gan_score", 0) or 0),
            state.get("recommended_scenario", "") or "",
        )
        with sqlite3.connect(_DB) as c:
            c.execute(
                "INSERT INTO audit_trail (ts,user_id,thread_id,question_hash,query_preview,"
                "models,rag_sources,compliance,gan_verdict,gan_score,final_scenario) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)", rec)
    except Exception:
        pass


def fetch_audit_trail(limit: int = 20, user_id: str = "") -> list[dict]:
    """최근 감사 레코드 조회 (UI 표시용)."""
    try:
        init_audit_table()
        q = ("SELECT " + ",".join(_COLS) + " FROM audit_trail "
             + ("WHERE user_id=? " if user_id else "")
             + "ORDER BY id DESC LIMIT ?")
        params = ((user_id, limit) if user_id else (limit,))
        with sqlite3.connect(_DB) as c:
            return [dict(zip(_COLS, row)) for row in c.execute(q, params).fetchall()]
    except Exception:
        return []
