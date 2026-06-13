"""ChromaDB 기반 세법 + JB상품 RAG 리트리버."""

import os, shutil, hashlib
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from data.tax_docs import TAX_DOCUMENTS

_DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
_SIG_PATH = os.path.join(_DB_PATH, ".content_sig")
_COLLECTION = "tax_law_2025"
# 빌드 로직이 바뀌면 올린다 → 기존 캐시(중복·옛 내용)를 강제 재생성
_BUILD_VERSION = "v2-clean-rebuild"
_vectorstore = None


def _content_sig() -> str:
    """문서 내용 + 빌드 버전 해시 — 내용/로직이 바뀌면 재구축 트리거."""
    h = hashlib.md5()
    h.update(_BUILD_VERSION.encode("utf-8"))
    for d in TAX_DOCUMENTS:
        h.update(d["id"].encode("utf-8"))
        h.update(d["content"].encode("utf-8"))
    return h.hexdigest()


def _embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def _build_vectorstore() -> Chroma:
    # 항상 빈 상태에서 시작 (중복 임베딩 누적 방지)
    shutil.rmtree(_DB_PATH, ignore_errors=True)
    docs = [
        Document(page_content=d["content"], metadata={"title": d["title"], "id": d["id"]})
        for d in TAX_DOCUMENTS
    ]
    vs = Chroma.from_documents(
        docs, _embeddings(),
        collection_name=_COLLECTION,
        persist_directory=_DB_PATH,
    )
    try:
        with open(_SIG_PATH, "w", encoding="utf-8") as f:
            f.write(_content_sig())
    except Exception:
        pass
    return vs


def _doc_count(vs: Chroma) -> int:
    try:
        return vs._collection.count()
    except Exception:
        return 0


def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        if os.path.exists(_DB_PATH):
            vs = Chroma(
                collection_name=_COLLECTION,
                embedding_function=_embeddings(),
                persist_directory=_DB_PATH,
            )
            # 문서 수 또는 내용(해시)이 달라졌으면 재빌드
            try:
                saved_sig = open(_SIG_PATH, encoding="utf-8").read().strip()
            except Exception:
                saved_sig = ""
            if _doc_count(vs) != len(TAX_DOCUMENTS) or saved_sig != _content_sig():
                vs = None
                shutil.rmtree(_DB_PATH, ignore_errors=True)
                vs = _build_vectorstore()
            _vectorstore = vs
        else:
            _vectorstore = _build_vectorstore()
    return _vectorstore


def retrieve(query: str, k: int = 3) -> str:
    """쿼리와 유사한 세법·상품 문서 청크를 반환합니다 (동일 문서 중복 제거)."""
    vs = get_vectorstore()
    docs = vs.similarity_search(query, k=k + 3)
    seen, unique = set(), []
    for d in docs:
        key = d.metadata.get("id") or d.page_content[:50]
        if key in seen:
            continue
        seen.add(key)
        unique.append(d)
        if len(unique) >= k:
            break
    return "\n\n---\n\n".join(f"[{d.metadata['title']}]\n{d.page_content}" for d in unique)
