from __future__ import annotations

import argparse
import gc
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from langchain_chroma import Chroma

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from transport_kb.rag_paths import chroma_safe_path, path_has_non_ascii  # noqa: E402
from transport_kb.rag_retrieval import (  # noqa: E402
    DEFAULT_DEVICE,
    DEFAULT_EMBEDDING_MODEL,
    build_embedding_model,
    evidence_to_document,
    load_formal_evidence,
)


HNSW_FILES = {
    "data_level0.bin",
    "header.bin",
    "length.bin",
    "link_lists.bin",
}
BATCH_SIZE = 3


def check_hnsw_files(persist_directory: Path) -> list[str]:
    present = {
        path.name
        for path in persist_directory.rglob("*")
        if path.is_file()
    }
    return sorted(HNSW_FILES & present)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_vector_store(
    database_path: Path,
    persist_directory: Path,
    embedding_model: Path = DEFAULT_EMBEDDING_MODEL,
    device: str = DEFAULT_DEVICE,
    reset: bool = False,
    report_path: Path | None = None,
) -> dict[str, object]:
    if not database_path.is_file():
        raise FileNotFoundError(f"SQLite 数据库不存在：{database_path}")
    if not (embedding_model / "config.json").is_file():
        raise FileNotFoundError(f"嵌入模型目录无效：{embedding_model}")

    records = load_formal_evidence(database_path)
    if not records:
        raise RuntimeError("SQLite 中没有可向量化的正式依据层证据")
    documents = [evidence_to_document(record) for record in records]
    evidence_ids = [document.metadata["evidence_id"] for document in documents]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise RuntimeError("正式依据层证据 ID 存在重复，无法作为向量主键")

    if reset and persist_directory.exists():
        shutil.rmtree(persist_directory)
    # Chroma HNSW native code cannot load indexes under non-ASCII Windows paths.
    logical_persist_directory = persist_directory
    persist_directory = chroma_safe_path(persist_directory, create=True)
    if reset and persist_directory.exists():
        # Safe path may differ from the logical project path; clear both.
        for path in {logical_persist_directory.absolute(), Path(persist_directory)}:
            if path.exists() and path.is_dir():
                shutil.rmtree(path)
        persist_directory = chroma_safe_path(logical_persist_directory, create=True)
    print(f"[>] Chroma 持久化路径：{persist_directory}")
    logical_abs = str(logical_persist_directory.absolute())
    persist_abs = str(persist_directory)  # already absolute/short; avoid resolve()
    if persist_abs.lower() != logical_abs.lower() or path_has_non_ascii(logical_abs):
        print(f"[>] 逻辑路径：{logical_persist_directory}")
        pointer = logical_persist_directory
        pointer.mkdir(parents=True, exist_ok=True)
        pointer.joinpath("CHROMA_PATH.txt").write_text(persist_abs + chr(10), encoding="utf-8")

    print(f"[>] 正在加载 HuggingFace BGE 嵌入模型：{embedding_model}")
    embeddings = build_embedding_model(embedding_model, device=device)
    print(f"[>] 正在使用 {device} 向量化 {len(documents)} 个证据片段（batch={BATCH_SIZE}）")
    vectorstore = Chroma(
        embedding_function=embeddings,
        persist_directory=str(persist_directory),
        collection_name="transport_safety_evidence",
        collection_metadata={
            "hnsw:space": "cosine",
            # Keep the persistent index synchronized during bulk ingestion.
            "hnsw:sync_threshold": 3,
            "hnsw:batch_size": 3,
        },
    )
    # Chroma 1.5.9 flushes the persistent HNSW index reliably on incremental
    # add_documents calls; a single bulk call can leave only SQLite metadata.
    total = len(documents)
    for start in range(0, total, BATCH_SIZE):
        batch = documents[start : start + BATCH_SIZE]
        vectorstore.add_documents(
            documents=batch,
            ids=[document.metadata["evidence_id"] for document in batch],
        )
        done = min(start + BATCH_SIZE, total)
        if done == total or done % 63 == 0 or start == 0:
            print(f"  - 已写入 {done}/{total}")

    # Force index materialization before tearing down the writer client.
    _ = vectorstore.similarity_search(documents[0].page_content, k=1)
    if hasattr(vectorstore, "persist"):
        vectorstore.persist()
    vectorstore._client.close()
    del vectorstore
    gc.collect()

    hnsw_files = check_hnsw_files(persist_directory)
    missing_hnsw_files = sorted(HNSW_FILES - set(hnsw_files))
    if missing_hnsw_files:
        # Some Chroma builds only flush segment files after an independent reopen.
        recovery = Chroma(
            persist_directory=str(persist_directory),
            embedding_function=embeddings,
            collection_name="transport_safety_evidence",
        )
        _ = recovery.similarity_search(documents[0].page_content, k=1)
        recovery._client.close()
        del recovery
        gc.collect()
        hnsw_files = check_hnsw_files(persist_directory)
        missing_hnsw_files = sorted(HNSW_FILES - set(hnsw_files))
    if missing_hnsw_files:
        raise RuntimeError(f"HNSW 索引文件未完整落盘，缺少：{missing_hnsw_files}")

    # Reopen independently so a successful build always means the index is usable.
    reopened = Chroma(
        persist_directory=str(persist_directory),
        embedding_function=embeddings,
        collection_name="transport_safety_evidence",
    )
    reopened_count = reopened._collection.count()
    if reopened_count != len(documents):
        raise RuntimeError(f"Chroma 重开后数量不符：{reopened_count} != {len(documents)}")
    probe_results = reopened.similarity_search(documents[0].page_content, k=1)
    if not probe_results:
        raise RuntimeError("Chroma 重开后无法完成相似度检索")
    probe_id = probe_results[0].metadata.get("evidence_id")
    if probe_id != documents[0].metadata["evidence_id"]:
        # Cosine self-search should usually return the same chunk; warn-level fail if empty only.
        print(f"  - 探测检索 top1={probe_id}（源={documents[0].metadata['evidence_id']}）")
    reopened._client.close()
    del reopened
    gc.collect()

    config_path = embedding_model / "config.json"
    config_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
    model_config = json.loads(config_path.read_text(encoding="utf-8"))
    database_stat = database_path.stat()
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "database": str(database_path.resolve()),
        "logical_persist_directory": str(logical_persist_directory.absolute()),
        "persist_directory": str(persist_directory),
        "database_size_bytes": database_stat.st_size,
        "database_mtime_utc": datetime.fromtimestamp(
            database_stat.st_mtime, tz=timezone.utc
        ).isoformat(timespec="seconds"),
        "database_sha256": file_sha256(database_path),
        "database_schema_version": "2",
        "chunk_type": "evidence_units",
        "chunk_count": len(documents),
        "publication_layer": "正式依据层",
        "review_status": "通过校验",
        "embedding_model": str(embedding_model.resolve()),
        "model_name_or_path": model_config.get("_name_or_path", ""),
        "model_type": model_config.get("model_type", ""),
        "embedding_dimension": model_config.get("hidden_size"),
        "max_position_embeddings": model_config.get("max_position_embeddings"),
        "model_config_sha256": config_hash,
        "device": device,
        "normalize_embeddings": True,
        "collection_name": "transport_safety_evidence",
        "distance": "cosine",
        "batch_size": BATCH_SIZE,
        "evidence_ids": evidence_ids,
        "content_hashes": {
            document.metadata["evidence_id"]: document.metadata["content_hash"]
            for document in documents
        },
    }
    (persist_directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    result = {
        **{key: value for key, value in manifest.items() if key not in {"evidence_ids", "content_hashes"}},
        "stored_count": reopened_count,
        "reopened_count": reopened_count,
        "hnsw_files": hnsw_files,
        "probe_top1_evidence_id": probe_id,
        "ids_unique": True,
        "status": "通过",
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"[>] 构建报告已写入：{report_path}")

    print("[OK] 向量库构建完成")
    print(
        json.dumps(
            {
                "chunk_count": result["chunk_count"],
                "stored_count": result["stored_count"],
                "embedding_dimension": result["embedding_dimension"],
                "device": result["device"],
                "hnsw_files": result["hnsw_files"],
                "output": str(persist_directory),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="为交通安全知识库构建本地 RAG 向量库")
    parser.add_argument(
        "--database",
        type=Path,
        default=PROJECT_ROOT / "data" / "transport_safety_kb.sqlite3",
    )
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "rag_chroma")
    parser.add_argument("--embedding-model", type=Path, default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--device", choices=("cuda", "cpu"), default=DEFAULT_DEVICE)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "data" / "reports" / "rag_vector_store_report.json",
    )
    args = parser.parse_args()
    build_vector_store(
        args.database.resolve(),
        args.output.resolve(),
        args.embedding_model.resolve(),
        args.device,
        args.reset,
        args.report.resolve(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
