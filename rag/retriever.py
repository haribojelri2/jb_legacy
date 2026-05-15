"""ChromaDB 기반 세법 + JB상품 RAG 리트리버."""

import os, shutil
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from data.tax_docs import TAX_DOCUMENTS

_DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
_COLLECTION = "tax_law_2025"
_vectorstore = None


def _embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def _build_vectorstore() -> Chroma:
    docs = [
        Document(page_content=d["content"], metadata={"title": d["title"], "id": d["id"]})
        for d in TAX_DOCUMENTS
    ]
    return Chroma.from_documents(
        docs, _embeddings(),
        collection_name=_COLLECTION,
        persist_directory=_DB_PATH,
    )


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
            # 문서 수가 달라졌으면 재빌드
            if _doc_count(vs) != len(TAX_DOCUMENTS):
                vs = None
                shutil.rmtree(_DB_PATH, ignore_errors=True)
                vs = _build_vectorstore()
            _vectorstore = vs
        else:
            _vectorstore = _build_vectorstore()
    return _vectorstore


def retrieve(query: str, k: int = 3) -> str:
    """쿼리와 유사한 세법·상품 문서 청크를 반환합니다."""
    vs = get_vectorstore()
    docs = vs.similarity_search(query, k=k)
    return "\n\n---\n\n".join(f"[{d.metadata['title']}]\n{d.page_content}" for d in docs)
