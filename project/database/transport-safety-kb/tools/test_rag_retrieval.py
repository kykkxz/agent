from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch
from langchain_chroma import Chroma

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from transport_kb.rag_paths import chroma_safe_path  # noqa: E402
from transport_kb.rag_retrieval import (  # noqa: E402
    DEFAULT_DEVICE,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_RERANKER_MODEL,
    LocalReranker,
    SparseBM25Retriever,
    build_embedding_model,
    get_all_docs,
    hybrid_retrieve,
    load_formal_evidence,
)


def load_questions(path: Path) -> list[dict[str, object]]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_collection(persist_directory: Path, expected_count: int, embedding_function) -> dict[str, object]:
    import sqlite3

    vectorstore = Chroma(
        persist_directory=str(persist_directory),
        embedding_function=embedding_function,
        collection_name="transport_safety_evidence",
    )
    api_count = vectorstore._collection.count()
    vectorstore._client.close()

    sqlite_count = None
    distinct_id_count = None
    chroma_db = persist_directory / "chroma.sqlite3"
    if chroma_db.is_file():
        with sqlite3.connect(chroma_db) as db:
            tables = {
                row[0]
                for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if {"embeddings", "segments", "collections"} <= tables:
                row = db.execute(
                    """
                    SELECT COUNT(*), COUNT(DISTINCT e.embedding_id)
                    FROM embeddings AS e
                    JOIN segments AS s ON s.id = e.segment_id
                    JOIN collections AS c ON c.id = s.collection
                    WHERE c.name = 'transport_safety_evidence'
                    """
                ).fetchone()
                sqlite_count, distinct_id_count = row[0], row[1]
            elif "embeddings" in tables:
                row = db.execute("SELECT COUNT(*), COUNT(DISTINCT embedding_id) FROM embeddings").fetchone()
                sqlite_count, distinct_id_count = row[0], row[1]

    ids_unique = True if distinct_id_count is None else sqlite_count == distinct_id_count
    count_matches = api_count == expected_count and (
        sqlite_count is None or sqlite_count == expected_count
    )
    return {
        "api_count": api_count,
        "stored_count": sqlite_count if sqlite_count is not None else api_count,
        "distinct_id_count": distinct_id_count if distinct_id_count is not None else api_count,
        "expected_count": expected_count,
        "count_matches": count_matches,
        "ids_unique": ids_unique,
    }


def evaluate_question(question: dict[str, object], records: list) -> dict[str, object]:
    query = str(question["question"])
    expected_terms = [str(item) for item in question.get("expected_title_terms", [])]
    expect_covered = question.get("expect_covered", True)
    if expect_covered is False:
        hit = len(records) == 0
        title_hit = hit
        citation_valid = True
    else:
        title_hit = not expected_terms or any(
            any(term in record.title for term in expected_terms) for record in records
        )
        citation_valid = bool(records) and all(
            record.review_status == "通过校验"
            and record.publication_layer == "正式依据层"
            and record.evidence_id
            and record.document_id
            and record.content_hash
            for record in records
        )
        hit = title_hit and citation_valid
    return {
        "hit": hit,
        "title_hit": title_hit,
        "citation_valid": citation_valid,
        "expect_covered": expect_covered,
        "expected_title_terms": expected_terms,
        "result_count": len(records),
        "top_results": [
            {
                "evidence_id": record.evidence_id,
                "title": record.title,
                "locator": record.locator,
                "document_type": record.document_type,
                "rerank_score": round(record.rerank_score, 6),
                "rrf_score": round(record.rrf_score, 6),
                "retrieval_ranks": record.retrieval_ranks or {},
            }
            for record in records
        ],
        "question": query,
    }


def run_test(
    database: Path,
    persist_directory: Path,
    questions_path: Path,
    embedding_model: Path,
    reranker_model: Path,
    device: str,
) -> dict[str, object]:
    pointer = persist_directory / "CHROMA_PATH.txt"
    if pointer.is_file():
        persist_directory = Path(pointer.read_text(encoding="utf-8").strip())
    elif persist_directory.is_dir():
        persist_directory = chroma_safe_path(persist_directory, create=False)
    if not persist_directory.is_dir():
        raise FileNotFoundError(f"向量库目录不存在，请先构建：{persist_directory}")
    manifest_path = persist_directory / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"缺少向量库 manifest：{manifest_path}")

    formal_records = load_formal_evidence(database)
    questions = load_questions(questions_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"[>] CUDA 可用：{torch.cuda.is_available()}，设备：{device}")
    print(f"[>] 正在加载嵌入模型：{embedding_model}")
    embeddings = build_embedding_model(embedding_model, device=device)
    collection_check = check_collection(persist_directory, len(formal_records), embeddings)
    print(
        "[>] 集合检查："
        f"api={collection_check['api_count']} "
        f"stored={collection_check['stored_count']} "
        f"expected={collection_check['expected_count']}"
    )
    vectorstore = Chroma(
        persist_directory=str(persist_directory),
        embedding_function=embeddings,
        collection_name="transport_safety_evidence",
    )
    print(f"[>] 正在加载重排模型：{reranker_model}")
    reranker = LocalReranker(reranker_model, device=device)
    print("[>] 预构建稀疏检索索引（BM25）")
    all_docs = get_all_docs(vectorstore)
    sparse_retriever = SparseBM25Retriever.from_documents(all_docs)

    results: list[dict[str, object]] = []
    for index, question in enumerate(questions, start=1):
        query = str(question["question"])
        records = hybrid_retrieve(
            query,
            vectorstore,
            reranker,
            database,
            retrieval_top_k=16,
            rrf_top_k=12,
            rerank_top_k=5,
            all_docs=all_docs,
            sparse_retriever=sparse_retriever,
        )
        evaluated = evaluate_question(question, records)
        result = {
            "id": question.get("id", f"Q{index:02d}"),
            **evaluated,
        }
        results.append(result)
        label = "命中" if result["hit"] else "未命中"
        print(f"[{index:02d}/{len(questions)}] {label} {query}")
        if records:
            print(f"    {records[0].title} / {records[0].locator} / {records[0].evidence_id}")
        elif question.get("expect_covered", True) is False:
            print("    （预期无覆盖，返回空结果）")

    covered = [item for item in results if item.get("expect_covered", True) is not False]
    uncovered = [item for item in results if item.get("expect_covered", True) is False]
    titled = [item for item in covered if item.get("expected_title_terms")]
    hit_count = sum(bool(item["hit"]) for item in results)
    covered_hits = sum(bool(item["hit"]) for item in covered)
    titled_hits = sum(bool(item["hit"]) for item in titled)
    uncovered_hits = sum(bool(item["hit"]) for item in uncovered)

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "database": str(database.resolve()),
        "vector_store": str(persist_directory.resolve()),
        "device": device,
        "cuda_available": torch.cuda.is_available(),
        "embedding_model": str(embedding_model.resolve()),
        "reranker_model": str(reranker_model.resolve()),
        "manifest_chunk_count": manifest.get("chunk_count"),
        "formal_evidence_count": len(formal_records),
        "collection_check": collection_check,
        "questions": len(results),
        "hits": hit_count,
        "hit_rate": round(hit_count / len(results), 4) if results else 0.0,
        "covered_questions": len(covered),
        "covered_hits": covered_hits,
        "covered_hit_rate": round(covered_hits / len(covered), 4) if covered else 0.0,
        "titled_questions": len(titled),
        "titled_hits": titled_hits,
        "titled_hit_rate": round(titled_hits / len(titled), 4) if titled else 0.0,
        "uncovered_questions": len(uncovered),
        "uncovered_correct": uncovered_hits,
        "results": results,
        "status": (
            "通过"
            if collection_check["count_matches"]
            and collection_check["ids_unique"]
            and (not titled or titled_hits == len(titled))
            and (not uncovered or uncovered_hits == len(uncovered))
            else "未通过"
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="测试交通安全知识库统一 RAG 检索")
    parser.add_argument(
        "--database",
        type=Path,
        default=PROJECT_ROOT / "data" / "transport_safety_kb.sqlite3",
    )
    parser.add_argument(
        "--vector-store",
        type=Path,
        default=PROJECT_ROOT / "data" / "rag_chroma",
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=PROJECT_ROOT / "config" / "acceptance_questions.json",
    )
    parser.add_argument("--embedding-model", type=Path, default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--reranker-model", type=Path, default=DEFAULT_RERANKER_MODEL)
    parser.add_argument("--device", choices=("cuda", "cpu"), default=DEFAULT_DEVICE)
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "data" / "reports" / "rag_retrieval_report.json",
    )
    args = parser.parse_args()
    report = run_test(
        args.database.resolve(),
        args.vector_store.resolve(),
        args.questions.resolve(),
        args.embedding_model.resolve(),
        args.reranker_model.resolve(),
        args.device,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "\n"
        + json.dumps(
            {
                key: report[key]
                for key in (
                    "status",
                    "questions",
                    "hits",
                    "hit_rate",
                    "covered_hit_rate",
                    "titled_hit_rate",
                    "uncovered_correct",
                    "collection_check",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"[>] 验收报告已写入：{args.report}")
    if report["status"] != "通过":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
