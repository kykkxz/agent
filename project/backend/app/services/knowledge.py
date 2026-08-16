from __future__ import annotations

import sqlite3
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT, settings


def _kb_root() -> Path:
    return PROJECT_ROOT / "database" / "transport-safety-kb"


def _ensure_kb_on_path() -> None:
    root = str(_kb_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def kb_available() -> bool:
    return Path(settings.kb_db_path).is_file()


def connect_kb() -> sqlite3.Connection:
    path = Path(settings.kb_db_path)
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


@lru_cache(maxsize=1)
def load_search_entries() -> list[dict[str, Any]]:
    if not kb_available():
        return []
    sql = """
        SELECT
            k.knowledge_id,
            k.topic,
            k.conclusion,
            k.document_id,
            k.invalidated,
            d.title,
            d.document_type,
            s.authority_level,
            d.source_id,
            s.publisher,
            s.source_uri
        FROM knowledge_entries AS k
        JOIN documents AS d ON d.document_id = k.document_id
        JOIN sources AS s ON s.source_id = d.source_id
        WHERE k.invalidated = 0
          AND k.review_status = '通过校验'
          AND k.publication_layer = '正式依据层'
    """
    with connect_kb() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(row) for row in rows]


def search_knowledge(query: str, limit: int = 5) -> list[dict[str, Any]]:
    if not query.strip() or not kb_available():
        return []
    _ensure_kb_on_path()
    from transport_kb.search import search

    hits = search(load_search_entries(), query, limit=limit)
    results: list[dict[str, Any]] = []
    for hit in hits:
        results.append(
            {
                "knowledge_id": hit.get("knowledge_id"),
                "title": hit.get("title") or hit.get("topic"),
                "topic": hit.get("topic"),
                "snippet": (hit.get("conclusion") or "")[:400],
                "document_type": hit.get("document_type"),
                "publisher": hit.get("publisher"),
                "source_uri": hit.get("source_uri"),
                "authority_level": hit.get("authority_level"),
                "score": hit.get("score"),
            }
        )
    return results


def list_documents(keyword: str = "", doc_type: str = "", page: int = 1, page_size: int = 20) -> tuple[list[dict[str, Any]], int]:
    if not kb_available():
        return [], 0
    where = ["1=1"]
    params: list[Any] = []
    if keyword:
        where.append("(d.title LIKE ? OR d.document_id LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if doc_type:
        where.append("d.document_type = ?")
        params.append(doc_type)
    where_sql = " AND ".join(where)
    count_sql = f"SELECT COUNT(*) FROM documents d WHERE {where_sql}"
    list_sql = f"""
        SELECT d.document_id, d.title, d.document_type, s.authority_level,
               d.version_status, d.review_status, d.publication_layer,
               s.publisher, s.source_uri
        FROM documents d
        JOIN sources s ON s.source_id = d.source_id
        WHERE {where_sql}
        ORDER BY s.authority_level, d.title
        LIMIT ? OFFSET ?
    """
    with connect_kb() as conn:
        total = conn.execute(count_sql, params).fetchone()[0]
        rows = conn.execute(list_sql, [*params, page_size, (page - 1) * page_size]).fetchall()
    return [dict(row) for row in rows], int(total)


def kb_overview() -> dict[str, Any]:
    if not kb_available():
        return {"available": False, "documents": 0, "knowledge_entries": 0, "evidence_units": 0}
    with connect_kb() as conn:
        documents = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        knowledge = conn.execute("SELECT COUNT(*) FROM knowledge_entries").fetchone()[0]
        evidence = conn.execute("SELECT COUNT(*) FROM evidence_units").fetchone()[0]
        types = conn.execute(
            "SELECT document_type, COUNT(*) AS c FROM documents GROUP BY document_type"
        ).fetchall()
    return {
        "available": True,
        "documents": documents,
        "knowledge_entries": knowledge,
        "evidence_units": evidence,
        "document_types": {row["document_type"]: row["c"] for row in types},
    }
