from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter
from collections.abc import Callable, Sequence
from contextlib import closing
from dataclasses import dataclass, replace
from math import log
from pathlib import Path
from typing import Any

import torch
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoModelForSequenceClassification, AutoTokenizer


DEFAULT_EMBEDDING_MODEL = Path(__file__).resolve().parents[2] / "bge-small-zh-v1.5"
DEFAULT_RERANKER_MODEL = Path(__file__).resolve().parents[2] / "bge-reranker-base"
DEFAULT_DEVICE = "cuda"
RRF_K = 60
# Keep regulatory instruments in the candidate pool even when accident reports dominate.
AUTHORITY_DOCUMENT_TYPES = ("法律", "行政法规", "监管文件")
AUTHORITY_DENSE_WEIGHT = 1.2


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    document_id: str
    knowledge_id: str
    title: str
    topic: str
    document_type: str
    locator: str
    text: str
    source_uri: str
    publisher: str
    authority_level: str
    version_status: str
    review_status: str
    publication_layer: str
    invalidated: bool
    content_hash: str
    rrf_score: float = 0.0
    rerank_score: float = 0.0
    retrieval_ranks: dict[str, int] | None = None


def normalized_hash(text: str) -> str:
    normalized = re.sub(r"\s+", "", text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def tokenize_for_bm25(text: str) -> list[str]:
    """Generate mixed Chinese bigrams and English tokens without extra tokenizers."""
    normalized = text.lower()
    latin_tokens = re.findall(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", normalized)
    chinese_segments = re.findall(r"[\u4e00-\u9fff]+", normalized)
    chinese_tokens: list[str] = []
    for segment in chinese_segments:
        chinese_tokens.extend(segment)
        chinese_tokens.extend(segment[index : index + 2] for index in range(len(segment) - 1))
    return latin_tokens + chinese_tokens


class SparseBM25Retriever:
    def __init__(
        self,
        docs: Sequence[Document],
        preprocess_func: Callable[[str], list[str]] = tokenize_for_bm25,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        self.docs = list(docs)
        self.preprocess_func = preprocess_func
        self.k1 = k1
        self.b = b
        self.k = 4
        tokenized_docs = [preprocess_func(doc.page_content) for doc in self.docs]
        self.term_frequencies = [Counter(tokens) for tokens in tokenized_docs]
        self.doc_lengths = [len(tokens) for tokens in tokenized_docs]
        self.avg_doc_length = (
            sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0.0
        )
        document_frequencies: Counter[str] = Counter()
        for term_frequency in self.term_frequencies:
            document_frequencies.update(term_frequency.keys())
        doc_count = len(self.docs)
        self.idf = {
            term: log(1 + (doc_count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequencies.items()
        }

    @classmethod
    def from_documents(cls, docs: Sequence[Document]) -> "SparseBM25Retriever":
        return cls(docs, preprocess_func=tokenize_for_bm25)

    def invoke(self, query: str) -> list[Document]:
        query_terms = Counter(self.preprocess_func(query))
        scored_docs: list[tuple[float, int, Document]] = []
        for index, (doc, term_frequency, doc_length) in enumerate(
            zip(self.docs, self.term_frequencies, self.doc_lengths)
        ):
            score = 0.0
            length_normalization = (
                doc_length / self.avg_doc_length if self.avg_doc_length else 0.0
            )
            for term, query_frequency in query_terms.items():
                frequency = term_frequency.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * length_normalization
                )
                score += (
                    self.idf.get(term, 0.0)
                    * (frequency * (self.k1 + 1) / denominator)
                    * query_frequency
                )
            scored_docs.append((score, index, doc))
        scored_docs.sort(key=lambda item: (-item[0], item[1]))
        return [doc for _, _, doc in scored_docs[: self.k]]


class LocalReranker:
    """Use the local BGE cross-encoder in the same role as the week5/rag example."""

    def __init__(self, model_path: str | Path, device: str = DEFAULT_DEVICE):
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            str(model_path), local_files_only=True
        )
        self.model.to(self.device)
        self.model.eval()

    def rank(
        self,
        query: str,
        docs: Sequence[Document],
        batch_size: int = 8,
    ) -> list[tuple[Document, float]]:
        if not docs:
            return []
        scores: list[float] = []
        with torch.inference_mode():
            for start in range(0, len(docs), batch_size):
                batch_docs = docs[start : start + batch_size]
                inputs = self.tokenizer(
                    [query] * len(batch_docs),
                    [doc.page_content for doc in batch_docs],
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                    max_length=512,
                )
                inputs = {name: tensor.to(self.device) for name, tensor in inputs.items()}
                logits = self.model(**inputs, return_dict=True).logits.view(-1)
                scores.extend(logits.float().cpu().tolist())
        return sorted(zip(docs, scores), key=lambda item: item[1], reverse=True)


def document_key(doc: Document) -> str:
    return str(doc.metadata.get("evidence_id", doc.page_content))


def reciprocal_rank_fusion(
    rankings: Sequence[tuple[Sequence[Document], float, str]],
    rrf_k: int = RRF_K,
    top_k: int = 8,
) -> list[Document]:
    scores: dict[str, float] = {}
    docs_by_key: dict[str, Document] = {}
    ranks_by_key: dict[str, dict[str, int]] = {}
    for docs, weight, retrieval_name in rankings:
        seen: set[str] = set()
        for rank, doc in enumerate(docs, start=1):
            key = document_key(doc)
            if key in seen:
                continue
            seen.add(key)
            docs_by_key.setdefault(key, doc)
            scores[key] = scores.get(key, 0.0) + weight / (rrf_k + rank)
            ranks_by_key.setdefault(key, {})[retrieval_name] = rank
    ordered = sorted(scores, key=lambda key: (-scores[key], key))[:top_k]
    result: list[Document] = []
    for key in ordered:
        metadata = dict(docs_by_key[key].metadata)
        metadata["rrf_score"] = scores[key]
        metadata["retrieval_ranks"] = ranks_by_key[key]
        result.append(Document(page_content=docs_by_key[key].page_content, metadata=metadata))
    return result


def build_embedding_model(model_path: str | Path, device: str = DEFAULT_DEVICE) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=str(model_path),
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )


def load_formal_evidence(database_path: Path) -> list[dict[str, Any]]:
    query = """
        SELECT
            e.evidence_id, e.document_id, e.locator, e.text, e.content_hash,
            k.knowledge_id, k.topic, k.risk_categories_json,
            d.title, d.document_type, d.version_status, d.review_status,
            d.publication_layer, k.invalidated,
            s.source_uri, s.publisher, s.authority_level
        FROM evidence_units AS e
        JOIN documents AS d ON d.document_id = e.document_id
        JOIN sources AS s ON s.source_id = d.source_id
        LEFT JOIN knowledge_citations AS kc ON kc.evidence_id = e.evidence_id
        LEFT JOIN knowledge_entries AS k ON k.knowledge_id = kc.knowledge_id
        WHERE d.review_status = '通过校验'
          AND d.publication_layer = '正式依据层'
          AND d.version_status IN ('当前有效候选', '不适用')
          AND k.knowledge_id IS NOT NULL
          AND k.review_status = '通过校验'
          AND k.publication_layer = '正式依据层'
          AND k.invalidated = 0
        ORDER BY e.evidence_id, kc.citation_order
    """
    with closing(sqlite3.connect(f"file:{database_path.resolve().as_posix()}?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(query).fetchall()
    records: dict[str, dict[str, Any]] = {}
    for row in rows:
        record = records.setdefault(row["evidence_id"], dict(row))
        if not record.get("knowledge_id") and row["knowledge_id"]:
            record["knowledge_id"] = row["knowledge_id"]
            record["topic"] = row["topic"]
            record["risk_categories_json"] = row["risk_categories_json"]
    return list(records.values())


def evidence_to_document(record: dict[str, Any]) -> Document:
    risk_categories = json.loads(record.get("risk_categories_json") or "[]")
    content = (
        f"标题：{record['title']}\n"
        f"主题：{record.get('topic') or record['title']}\n"
        f"文档类型：{record['document_type']}\n"
        f"定位：{record['locator']}\n"
        f"风险类别：{'、'.join(risk_categories)}\n"
        f"正文：\n{record['text']}"
    )
    metadata = {
        "evidence_id": record["evidence_id"],
        "document_id": record["document_id"],
        "knowledge_id": record.get("knowledge_id") or "",
        "title": record["title"],
        "document_type": record["document_type"],
        "locator": record["locator"],
        "source_uri": record["source_uri"],
        "authority_level": record["authority_level"],
        "version_status": record["version_status"],
        "review_status": record["review_status"],
        "publication_layer": record["publication_layer"],
        "invalidated": int(record["invalidated"]),
        "content_hash": record["content_hash"],
    }
    return Document(page_content=content, metadata=metadata)


def validate_retrieved_ids(database_path: Path, evidence_ids: Sequence[str]) -> dict[str, EvidenceRecord]:
    if not evidence_ids:
        return {}
    placeholders = ", ".join("?" for _ in evidence_ids)
    query = f"""
        SELECT
            e.evidence_id, e.document_id, e.locator, e.text, e.content_hash,
            k.knowledge_id, k.topic,
            d.title, d.document_type, d.version_status, d.review_status,
            d.publication_layer, k.invalidated,
            s.source_uri, s.publisher, s.authority_level
        FROM evidence_units AS e
        JOIN documents AS d ON d.document_id = e.document_id
        JOIN sources AS s ON s.source_id = d.source_id
        LEFT JOIN knowledge_citations AS kc ON kc.evidence_id = e.evidence_id
        LEFT JOIN knowledge_entries AS k ON k.knowledge_id = kc.knowledge_id
        WHERE e.evidence_id IN ({placeholders})
          AND d.review_status = '通过校验'
          AND d.publication_layer = '正式依据层'
          AND d.version_status IN ('当前有效候选', '不适用')
          AND k.knowledge_id IS NOT NULL
          AND k.review_status = '通过校验'
          AND k.publication_layer = '正式依据层'
          AND k.invalidated = 0
    """
    with closing(sqlite3.connect(f"file:{database_path.resolve().as_posix()}?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(query, list(evidence_ids)).fetchall()
    result: dict[str, EvidenceRecord] = {}
    for row in rows:
        if row["evidence_id"] in result:
            continue
        if normalized_hash(row["text"]) != row["content_hash"]:
            continue
        result[row["evidence_id"]] = EvidenceRecord(
            evidence_id=row["evidence_id"], document_id=row["document_id"],
            knowledge_id=row["knowledge_id"] or "", title=row["title"],
            topic=row["topic"] or row["title"], document_type=row["document_type"],
            locator=row["locator"], text=row["text"], source_uri=row["source_uri"],
            publisher=row["publisher"], authority_level=row["authority_level"],
            version_status=row["version_status"], review_status=row["review_status"],
            publication_layer=row["publication_layer"], invalidated=bool(row["invalidated"] or 0),
            content_hash=row["content_hash"],
        )
    return result


def get_all_docs(vectorstore: Chroma) -> list[Document]:
    data = vectorstore.get(include=["documents", "metadatas"])
    return [
        Document(page_content=content, metadata=metadata or {})
        for content, metadata in zip(data["documents"], data["metadatas"])
        if content
    ]


def authority_dense_search(
    vectorstore: Chroma,
    query: str,
    *,
    k: int,
    all_docs: Sequence[Document] | None = None,
) -> list[Document]:
    """Dense retrieve restricted to high-authority instrument types."""
    if k <= 0:
        return []
    try:
        return vectorstore.similarity_search(
            query,
            k=k,
            filter={"document_type": {"$in": list(AUTHORITY_DOCUMENT_TYPES)}},
        )
    except Exception:
        # Fallback for stores/backends that reject metadata filters.
        pool = [
            doc
            for doc in (all_docs if all_docs is not None else get_all_docs(vectorstore))
            if doc.metadata.get("document_type") in AUTHORITY_DOCUMENT_TYPES
        ]
        if not pool:
            return []
        # Approximate with unrestricted dense then filter, preserving order.
        unrestricted = vectorstore.similarity_search(query, k=min(max(k * 8, k), 64))
        filtered = [
            doc
            for doc in unrestricted
            if doc.metadata.get("document_type") in AUTHORITY_DOCUMENT_TYPES
        ]
        if filtered:
            return filtered[:k]
        return pool[:k]


def hybrid_retrieve(
    query: str,
    vectorstore: Chroma,
    reranker: LocalReranker,
    database_path: Path,
    retrieval_top_k: int = 16,
    rrf_top_k: int = 12,
    rerank_top_k: int = 5,
    sparse_retriever_factory: Callable[[Sequence[Document]], SparseBM25Retriever] | None = None,
    all_docs: Sequence[Document] | None = None,
    sparse_retriever: SparseBM25Retriever | None = None,
) -> list[EvidenceRecord]:
    # Mirror keyword-search policy: unpublished/internal content is not covered.
    if "未公开" in query or "内部未公开" in query:
        return []
    docs = list(all_docs) if all_docs is not None else get_all_docs(vectorstore)
    if not docs:
        return []
    if sparse_retriever is not None:
        sparse = sparse_retriever
    else:
        sparse = (sparse_retriever_factory or SparseBM25Retriever.from_documents)(docs)
    sparse.k = min(retrieval_top_k, len(docs))
    sparse_docs = sparse.invoke(query)
    dense_docs = vectorstore.similarity_search(query, k=min(retrieval_top_k, len(docs)))
    authority_k = min(max(retrieval_top_k // 2, 8), len(docs))
    authority_docs = authority_dense_search(
        vectorstore,
        query,
        k=authority_k,
        all_docs=docs,
    )
    fused = reciprocal_rank_fusion(
        [
            (dense_docs, 1.0, "dense"),
            (sparse_docs, 1.0, "sparse"),
            (authority_docs, AUTHORITY_DENSE_WEIGHT, "authority_dense"),
        ],
        top_k=min(rrf_top_k, len(docs)),
    )
    reranked = reranker.rank(query, fused)[:rerank_top_k]
    ids = [document_key(doc) for doc, _ in reranked]
    validated = validate_retrieved_ids(database_path, ids)
    results: list[EvidenceRecord] = []
    for doc, rerank_score in reranked:
        evidence_id = document_key(doc)
        record = validated.get(evidence_id)
        if record is None:
            continue
        record = replace(
            record,
            rrf_score=float(doc.metadata.get("rrf_score", 0.0)),
            rerank_score=float(rerank_score),
            retrieval_ranks=doc.metadata.get("retrieval_ranks", {}),
        )
        results.append(record)
    return results


def format_context(records: Sequence[EvidenceRecord]) -> str:
    return "\n\n".join(
        f"【证据 {index}】\n标题：{record.title}\n定位：{record.locator}\n"
        f"正文：{record.text}\n来源：{record.source_uri}"
        for index, record in enumerate(records, start=1)
    )
