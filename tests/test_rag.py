"""RAG 리트리버 테스트 — 청킹·오프라인 폴백은 항상, 임베딩 검색은 API 키 있을 때만."""

import os

import pytest

from rag.retriever import _chunk_documents, _keyword_fallback, retrieve_scored

_HAS_KEY = bool(os.getenv("OPENAI_API_KEY"))

# 골드 평가셋: 질의 → 기대 출처 문서 id
_GOLD = [
    ("가업승계 증여세 특례 요건 알려줘", "succession_gift_tax_special"),
    ("권리금 팔면 세금 어떻게 내나요 기타소득", "goodwill_income_tax"),
    ("2025년 종합소득세 세율 구간", "income_tax_rates_2025"),
    ("가업상속공제 상속세 얼마까지", "business_inheritance_deduction"),
]


def test_chunking_expands_corpus():
    """문서 6개가 청킹으로 여러 청크로 분할돼 검색 변별력을 확보한다."""
    chunks = _chunk_documents()
    assert len(chunks) > len(set(c.metadata["id"] for c in chunks))  # 문서당 다수 청크
    assert all(c.metadata.get("title") for c in chunks)              # 출처 메타 보존


def test_keyword_fallback_offline():
    """임베딩 없이도 키워드 폴백이 관련 문서를 찾는다 (시연장 안전망)."""
    res = _keyword_fallback("가업승계 증여세 특례", k=3)
    assert res
    assert res[0]["id"] == "succession_gift_tax_special"
    assert res[0].get("fallback") is True


@pytest.mark.skipif(not _HAS_KEY, reason="OPENAI_API_KEY 필요 (임베딩 검색)")
def test_gold_recall_at_3():
    """골드 질의마다 기대 출처가 상위 3개 안에 있어야 한다 (recall@3)."""
    hits = 0
    for query, expected_id in _GOLD:
        results = retrieve_scored(query, k=3)
        if any(r["id"] == expected_id for r in results):
            hits += 1
    assert hits >= 3, f"recall@3 미달: {hits}/{len(_GOLD)}"
