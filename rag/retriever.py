"""ChromaDB 기반 세법 + JB상품 RAG 리트리버.

고도화:
  - 조문 단위 청킹(RecursiveCharacterTextSplitter) → 문서 6개를 다수 청크로 분할해
    유사도 검색이 실제로 변별력을 갖도록 함
  - 유사도 점수·출처(title/id) 구조화 반환 → 응답 근거 인용·UI 각주 가능
  - 임계값 미달 청크 제외, 임베딩 API 장애 시 오프라인 키워드 폴백(시연장 리스크 대비)
"""

import os, re, shutil, hashlib
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from data.tax_docs import TAX_DOCUMENTS

_DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
_SIG_PATH = os.path.join(_DB_PATH, ".content_sig")
_COLLECTION = "tax_law_2025"
# 빌드 로직이 바뀌면 올린다 → 기존 캐시(중복·옛 내용)를 강제 재생성
_BUILD_VERSION = "v4-cosine"
# cosine 거리(0=동일 ~ 2=정반대) 기반 필터. 이 값 초과 청크는 무관으로 간주해 제외.
# 정규화된 임베딩에서 관련 청크는 대개 0.6 이하, 무관 청크는 0.9 이상.
_DISTANCE_MAX = 0.85
_vectorstore = None

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=700, chunk_overlap=120,
    separators=["\n\n[", "\n\n", "\n", " ", ""],
)


def _chunk_documents() -> list[Document]:
    """문서를 조문/섹션 단위 청크로 분할하고 출처 메타데이터를 부여."""
    docs = []
    for d in TAX_DOCUMENTS:
        for i, chunk in enumerate(_splitter.split_text(d["content"])):
            docs.append(Document(
                page_content=chunk,
                metadata={"title": d["title"], "id": d["id"], "chunk": i},
            ))
    return docs


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
    # hnsw:space=cosine 명시 → 거리 값이 [0,2]로 well-defined (기본 L2는 관련도 변환이
    # 0~1을 벗어나 임계값 필터가 무의미해지는 경고 발생)
    _meta = {"hnsw:space": "cosine"}
    vs = Chroma(
        collection_name=_COLLECTION,
        embedding_function=_embeddings(),
        persist_directory=_DB_PATH,
        collection_metadata=_meta,
    )
    # rmtree가 파일 잠금으로 실패해도 논리적 중복이 남지 않도록 컬렉션을 비우고 재적재
    try:
        vs.delete_collection()
    except Exception:
        pass
    vs = Chroma.from_documents(
        _chunk_documents(), _embeddings(),
        collection_name=_COLLECTION,
        persist_directory=_DB_PATH,
        collection_metadata=_meta,
    )
    try:
        with open(_SIG_PATH, "w", encoding="utf-8") as f:
            f.write(_content_sig())
    except Exception:
        pass
    return vs


def _expected_chunk_count() -> int:
    return len(_chunk_documents())


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
                collection_metadata={"hnsw:space": "cosine"},
            )
            # 청크 수 또는 내용(해시)이 달라졌으면 재빌드
            try:
                saved_sig = open(_SIG_PATH, encoding="utf-8").read().strip()
            except Exception:
                saved_sig = ""
            if _doc_count(vs) != _expected_chunk_count() or saved_sig != _content_sig():
                shutil.rmtree(_DB_PATH, ignore_errors=True)
                vs = _build_vectorstore()
            _vectorstore = vs
        else:
            _vectorstore = _build_vectorstore()
    return _vectorstore


def _keyword_fallback(query: str, k: int) -> list[dict]:
    """임베딩 장애 시 오프라인 키워드 중첩 점수로 문서 검색 (시연장 안전망)."""
    tokens = [t for t in re.findall(r"[가-힣A-Za-z0-9]+", query) if len(t) >= 2]
    scored = []
    for d in TAX_DOCUMENTS:
        text = d["content"]
        hits = sum(text.count(tok) for tok in tokens)
        if hits:
            scored.append({"id": d["id"], "title": d["title"],
                           "content": text.strip()[:700], "score": float(hits), "fallback": True})
    scored.sort(key=lambda x: -x["score"])
    return scored[:k]


def retrieve_scored(query: str, k: int = 3) -> list[dict]:
    """유사도 점수·출처 포함 검색 결과 반환.

    반환: [{id, title, content, score}]. 임계값 미달은 제외, 동일 문서는 최상위 청크만.
    임베딩/네트워크 장애 시 오프라인 키워드 폴백으로 전환한다.
    """
    try:
        vs = get_vectorstore()
        # cosine 거리 반환 (0=동일 ~ 2=정반대). 관련도 변환의 0~1 벗어남 경고를 피하고
        # 거리 임계값으로 명확히 필터. 낮을수록 관련도가 높다.
        pairs = vs.similarity_search_with_score(query, k=k + 5)
    except Exception:
        return _keyword_fallback(query, k)

    seen, out = set(), []
    for doc, distance in pairs:
        if distance > _DISTANCE_MAX:
            continue
        did = doc.metadata.get("id")
        if did in seen:
            continue
        seen.add(did)
        out.append({
            "id": did,
            "title": doc.metadata.get("title", ""),
            "content": doc.page_content.strip(),
            # 표시용 유사도 = 1 - cosine거리/2 → [0,1]로 정규화
            "score": round(max(0.0, 1.0 - float(distance) / 2.0), 3),
        })
        if len(out) >= k:
            break
    return out


def retrieve(query: str, k: int = 3) -> str:
    """쿼리와 유사한 세법·상품 청크를 결합 문자열로 반환 (기존 호출부 호환).

    각 청크에 [출처 n] 라벨과 유사도를 붙여 LLM이 근거를 인용할 수 있게 한다.
    """
    results = retrieve_scored(query, k)
    if not results:
        return ""
    blocks = []
    for i, r in enumerate(results, 1):
        score_note = f" (유사도 {r['score']})" if not r.get("fallback") else " (키워드 검색)"
        blocks.append(f"[출처 {i}: {r['title']}{score_note}]\n{r['content']}")
    return "\n\n---\n\n".join(blocks)
