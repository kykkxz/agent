from __future__ import annotations

import argparse
import json
import sys
import time
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
    format_context,
    get_all_docs,
    hybrid_retrieve,
)


# 20 条模拟查询：覆盖法律/条例/监管/规程/事故/负例
SIMULATED_QUERIES: list[dict[str, object]] = [
    {
        "id": "S01",
        "category": "法律",
        "command": 'rag-search --query "安全生产工作的方针是什么？" --limit 5',
        "query": "安全生产工作的方针是什么？",
        "expect_title_terms": ["安全生产法"],
    },
    {
        "id": "S02",
        "category": "法律",
        "command": 'rag-search --query "生产经营单位主要负责人的安全生产职责有哪些？" --limit 5',
        "query": "生产经营单位主要负责人的安全生产职责有哪些？",
        "expect_title_terms": ["安全生产法"],
    },
    {
        "id": "S03",
        "category": "法律",
        "command": 'rag-search --query "从业人员发现事故隐患应当如何报告？" --limit 5',
        "query": "从业人员发现事故隐患应当如何报告？",
        "expect_title_terms": ["安全生产法"],
    },
    {
        "id": "S04",
        "category": "法律",
        "command": 'rag-search --query "特种作业人员上岗有什么要求？" --limit 5',
        "query": "特种作业人员上岗有什么要求？",
        "expect_title_terms": ["安全生产法"],
    },
    {
        "id": "S05",
        "category": "法律",
        "command": 'rag-search --query "发生生产安全事故后主要负责人应如何处置？" --limit 5',
        "query": "发生生产安全事故后主要负责人应如何处置？",
        "expect_title_terms": ["安全生产法"],
    },
    {
        "id": "S06",
        "category": "行政法规",
        "command": 'rag-search --query "建设单位有哪些安全生产责任？" --limit 5',
        "query": "建设单位有哪些安全生产责任？",
        "expect_title_terms": ["建设工程安全生产管理条例"],
    },
    {
        "id": "S07",
        "category": "行政法规",
        "command": 'rag-search --query "施工单位项目负责人有哪些施工安全职责？" --limit 5',
        "query": "施工单位项目负责人有哪些施工安全职责？",
        "expect_title_terms": ["建设工程安全生产管理条例"],
    },
    {
        "id": "S08",
        "category": "行政法规",
        "command": 'rag-search --query "施工现场发生事故后应如何报告？" --limit 5',
        "query": "施工现场发生事故后应如何报告？",
        "expect_title_terms": ["建设工程安全生产管理条例"],
    },
    {
        "id": "S09",
        "category": "行政法规",
        "command": 'rag-search --query "深基坑工程是否需要专项施工方案？" --limit 5',
        "query": "深基坑工程是否需要专项施工方案？",
        "expect_title_terms": ["建设工程安全生产管理条例"],
    },
    {
        "id": "S10",
        "category": "行政法规",
        "command": 'rag-search --query "监理单位发现安全事故隐患应如何处理？" --limit 5',
        "query": "监理单位发现安全事故隐患应如何处理？",
        "expect_title_terms": ["建设工程安全生产管理条例"],
    },
    {
        "id": "S11",
        "category": "监管文件",
        "command": 'rag-search --query "交通运输重大事故隐患如何判定？" --limit 5',
        "query": "交通运输重大事故隐患如何判定？",
        "expect_title_terms": ["重大事故隐患"],
    },
    {
        "id": "S12",
        "category": "监管文件",
        "command": 'rag-search --query "公路水运工程生产安全重大事故隐患判定标准有哪些？" --limit 5',
        "query": "公路水运工程生产安全重大事故隐患判定标准有哪些？",
        "expect_title_terms": ["公路水运"],
    },
    {
        "id": "S13",
        "category": "操作规程",
        "command": 'rag-search --query "起重吊装作业安全操作有哪些要求？" --limit 5',
        "query": "起重吊装作业安全操作有哪些要求？",
        "expect_title_terms": ["起重"],
    },
    {
        "id": "S14",
        "category": "操作规程",
        "command": 'rag-search --query "脚手架搭设和拆除应注意什么？" --limit 5',
        "query": "脚手架搭设和拆除应注意什么？",
        "expect_title_terms": ["架子"],
    },
    {
        "id": "S15",
        "category": "应急预案",
        "command": 'rag-search --query "公路水运工程生产安全事故应急预案有什么要求？" --limit 5',
        "query": "公路水运工程生产安全事故应急预案有什么要求？",
        "expect_title_terms": ["应急"],
    },
    {
        "id": "S16",
        "category": "事故案例",
        "command": 'rag-search --query "典型交通事故的直接原因是什么？" --limit 5',
        "query": "典型交通事故的直接原因是什么？",
        "expect_title_terms": ["事故"],
    },
    {
        "id": "S17",
        "category": "事故案例",
        "command": 'rag-search --query "事故调查报告通常提出哪些整改措施？" --limit 5',
        "query": "事故调查报告通常提出哪些整改措施？",
        "expect_title_terms": ["事故"],
    },
    {
        "id": "S18",
        "category": "综合法规",
        "command": 'rag-search --query "重大危险源应如何管理？" --limit 5',
        "query": "重大危险源应如何管理？",
        "expect_title_terms": ["安全生产法"],
    },
    {
        "id": "S19",
        "category": "综合法规",
        "command": 'rag-search --query "专职安全生产管理人员如何开展现场监督？" --limit 5',
        "query": "专职安全生产管理人员如何开展现场监督？",
        "expect_title_terms": ["建设工程安全生产管理条例"],
    },
    {
        "id": "S20",
        "category": "负例",
        "command": 'rag-search --query "某企业未公开的内部应急预案具体内容是什么？" --limit 5',
        "query": "某企业未公开的内部应急预案具体内容是什么？",
        "expect_title_terms": [],
        "expect_empty": True,
    },
]


def record_to_dict(record) -> dict[str, object]:
    return {
        "evidence_id": record.evidence_id,
        "document_id": record.document_id,
        "knowledge_id": record.knowledge_id,
        "title": record.title,
        "topic": record.topic,
        "document_type": record.document_type,
        "locator": record.locator,
        "text": record.text,
        "source_uri": record.source_uri,
        "publisher": record.publisher,
        "authority_level": record.authority_level,
        "publication_layer": record.publication_layer,
        "review_status": record.review_status,
        "content_hash": record.content_hash,
        "rrf_score": round(float(record.rrf_score), 6),
        "rerank_score": round(float(record.rerank_score), 6),
        "retrieval_ranks": record.retrieval_ranks or {},
    }


def evaluate_case(case: dict[str, object], records: list) -> dict[str, object]:
    expect_empty = bool(case.get("expect_empty", False))
    expected_terms = [str(item) for item in case.get("expect_title_terms", [])]
    if expect_empty:
        hit = len(records) == 0
        title_hit = hit
    elif expected_terms:
        title_hit = any(
            any(term in record.title for term in expected_terms) for record in records
        )
        hit = title_hit and bool(records)
    else:
        title_hit = bool(records)
        hit = bool(records)
    return {
        "hit": hit,
        "title_hit": title_hit,
        "expect_empty": expect_empty,
        "expected_title_terms": expected_terms,
        "result_count": len(records),
    }


def run_simulation(
    database: Path,
    vector_store: Path,
    embedding_model: Path,
    reranker_model: Path,
    device: str,
    limit: int,
    retrieval_top_k: int,
    rrf_top_k: int,
) -> dict[str, object]:
    if device == "cuda" and not torch.cuda.is_available():
        print("[!] CUDA 不可用，回退到 cpu", file=sys.stderr)
        device = "cpu"

    persist_directory = chroma_safe_path(vector_store, create=False)
    print(f"[>] device={device}", flush=True)
    print(f"[>] database={database}", flush=True)
    print(f"[>] vector_store={persist_directory}", flush=True)
    print(f"[>] loading embedding: {embedding_model}", flush=True)
    embeddings = build_embedding_model(embedding_model, device=device)
    vectorstore = Chroma(
        embedding_function=embeddings,
        persist_directory=str(persist_directory),
        collection_name="transport_safety_evidence",
    )
    print(f"[>] loading reranker: {reranker_model}", flush=True)
    reranker = LocalReranker(reranker_model, device=device)
    print("[>] building sparse index...", flush=True)
    all_docs = get_all_docs(vectorstore)
    sparse = SparseBM25Retriever.from_documents(all_docs)

    results: list[dict[str, object]] = []
    total_started = time.perf_counter()
    for index, case in enumerate(SIMULATED_QUERIES, start=1):
        query = str(case["query"])
        started = time.perf_counter()
        records = hybrid_retrieve(
            query,
            vectorstore,
            reranker,
            database,
            retrieval_top_k=retrieval_top_k,
            rrf_top_k=rrf_top_k,
            rerank_top_k=limit,
            all_docs=all_docs,
            sparse_retriever=sparse,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        evaluation = evaluate_case(case, records)
        top_results = [record_to_dict(record) for record in records]
        item = {
            "id": case["id"],
            "category": case["category"],
            "command": case["command"],
            "query": query,
            "elapsed_ms": elapsed_ms,
            **evaluation,
            "top_results": top_results,
            "context": format_context(records) if records else "",
            "response": {
                "query": query,
                "scenario": "cli-simulation",
                "top_k": limit,
                "result_count": len(top_results),
                "results": [
                    {
                        "evidence_id": row["evidence_id"],
                        "title": row["title"],
                        "locator": row["locator"],
                        "document_type": row["document_type"],
                        "text": row["text"],
                        "source_uri": row["source_uri"],
                        "content_hash": row["content_hash"],
                        "score": row["rerank_score"],
                        "rrf_score": row["rrf_score"],
                        "retrieval_ranks": row["retrieval_ranks"],
                    }
                    for row in top_results
                ],
            },
        }
        results.append(item)
        label = "命中" if item["hit"] else "未命中"
        top_title = top_results[0]["title"] if top_results else "（空结果）"
        top_locator = top_results[0]["locator"] if top_results else "-"
        print(
            f"[{index:02d}/{len(SIMULATED_QUERIES)}] {label} {case['id']} "
            f"{elapsed_ms}ms | {query}",
            flush=True,
        )
        print(f"    {top_title} / {top_locator}", flush=True)

    hit_count = sum(1 for item in results if item["hit"])
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "database": str(database),
        "vector_store": str(persist_directory),
        "embedding_model": str(embedding_model),
        "reranker_model": str(reranker_model),
        "device": device,
        "cuda_available": torch.cuda.is_available(),
        "pool_size": len(all_docs),
        "params": {
            "limit": limit,
            "retrieval_top_k": retrieval_top_k,
            "rrf_top_k": rrf_top_k,
        },
        "questions": len(results),
        "hits": hit_count,
        "hit_rate": round(hit_count / len(results), 4) if results else 0.0,
        "total_elapsed_ms": round((time.perf_counter() - total_started) * 1000, 1),
        "status": "通过" if hit_count == len(results) else "未通过",
        "results": results,
    }
    return report


def write_markdown(report: dict[str, object], path: Path) -> None:
    from render_rag_simulate_report import write_markdown as _write_markdown

    _write_markdown(report, path)


def write_plaintext(report: dict[str, object], path: Path) -> None:
    from render_rag_simulate_report import write_plaintext as _write_plaintext

    _write_plaintext(report, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="模拟 20 条 rag-search 查询并记录返回结果")
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
    parser.add_argument("--embedding-model", type=Path, default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--reranker-model", type=Path, default=DEFAULT_RERANKER_MODEL)
    parser.add_argument("--device", choices=("cuda", "cpu"), default=DEFAULT_DEVICE)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--retrieval-top-k", type=int, default=16)
    parser.add_argument("--rrf-top-k", type=int, default=12)
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "data" / "reports" / "rag_simulate_20_report.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=PROJECT_ROOT / "data" / "reports" / "rag_simulate_20_report.md",
    )
    parser.add_argument(
        "--plaintext",
        type=Path,
        default=PROJECT_ROOT / "data" / "reports" / "rag_simulate_20_report.txt",
    )
    args = parser.parse_args()

    report = run_simulation(
        args.database.resolve(),
        args.vector_store.resolve(),
        args.embedding_model.resolve(),
        args.reranker_model.resolve(),
        args.device,
        args.limit,
        args.retrieval_top_k,
        args.rrf_top_k,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.markdown)
    write_plaintext(report, args.plaintext)

    summary = {
        "status": report["status"],
        "questions": report["questions"],
        "hits": report["hits"],
        "hit_rate": report["hit_rate"],
        "total_elapsed_ms": report["total_elapsed_ms"],
        "report": str(args.report),
        "markdown": str(args.markdown),
        "plaintext": str(args.plaintext),
    }
    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0 if report["status"] == "通过" else 2


if __name__ == "__main__":
    raise SystemExit(main())
