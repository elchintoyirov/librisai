"""
retriever.py — Hybrid BM25 + FAISS retriever.

BM25 handles exact Uzbek keyword matches; FAISS handles semantic similarity.
Results are merged with Reciprocal Rank Fusion (RRF) — a simple, effective
way to combine two ranked lists without needing normalised scores.
"""

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever

# Must match the model used during ingestion (ingest.py)
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_embeddings: HuggingFaceEmbeddings | None = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


class HybridRetriever(BaseRetriever):
    """Merge BM25 and FAISS results using Reciprocal Rank Fusion."""

    bm25: BM25Retriever
    faiss_retriever: object          # FAISS VectorStoreRetriever
    k: int = 6
    bm25_weight: float = 0.6
    faiss_weight: float = 0.4
    rrf_k: int = 60                  # RRF constant

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        bm25_docs  = self.bm25.invoke(query)
        faiss_docs = self.faiss_retriever.invoke(query)

        # Reciprocal Rank Fusion
        scores: dict[str, float] = {}
        id_to_doc: dict[str, Document] = {}

        for rank, doc in enumerate(bm25_docs):
            key = doc.page_content
            scores[key]    = scores.get(key, 0) + self.bm25_weight  / (self.rrf_k + rank + 1)
            id_to_doc[key] = doc

        for rank, doc in enumerate(faiss_docs):
            key = doc.page_content
            scores[key]    = scores.get(key, 0) + self.faiss_weight / (self.rrf_k + rank + 1)
            id_to_doc[key] = doc

        ranked = sorted(scores, key=scores.__getitem__, reverse=True)
        return [id_to_doc[k] for k in ranked[: self.k]]


def load_retriever(index_path: str | Path, k: int = 6) -> HybridRetriever:
    """
    Load a hybrid BM25 + FAISS retriever.

    Documents are extracted directly from the FAISS docstore —
    no re-ingestion needed.
    """
    vectorstore = FAISS.load_local(
        str(index_path),
        _get_embeddings(),
        allow_dangerous_deserialization=True,
    )

    all_docs = list(vectorstore.docstore._dict.values())

    bm25 = BM25Retriever.from_documents(all_docs, k=k)
    faiss_ret = vectorstore.as_retriever(search_kwargs={"k": k})

    return HybridRetriever(bm25=bm25, faiss_retriever=faiss_ret, k=k)
