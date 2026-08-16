"""Promote local authoritative 法律/行政法规 into formal RAG layer."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

VALIDATED_REVIEW_STATUS = "通过校验"
VALIDATED_PUBLICATION_LAYER = "正式依据层"
TARGET_TYPES = ("法律", "行政法规")


def promote(database: Path) -> dict:
    database = database.resolve()
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        docs = connection.execute(
            """
            SELECT document_id, title, document_type, publication_layer, review_status
            FROM documents
            WHERE document_type IN (?, ?)
              AND (
                publication_layer != ?
                OR review_status != ?
              )
            """,
            (*TARGET_TYPES, VALIDATED_PUBLICATION_LAYER, VALIDATED_REVIEW_STATUS),
        ).fetchall()
        doc_ids = [row["document_id"] for row in docs]
        if not doc_ids:
            return {
                "database": str(database),
                "promoted_documents": 0,
                "promoted_knowledge_entries": 0,
                "documents": [],
            }
        placeholders = ", ".join("?" for _ in doc_ids)
        connection.execute(
            f"""
            UPDATE documents
            SET review_status = ?, publication_layer = ?
            WHERE document_id IN ({placeholders})
            """,
            [VALIDATED_REVIEW_STATUS, VALIDATED_PUBLICATION_LAYER, *doc_ids],
        )
        knowledge_count = connection.execute(
            f"""
            SELECT COUNT(*) FROM knowledge_entries
            WHERE document_id IN ({placeholders})
            """,
            doc_ids,
        ).fetchone()[0]
        connection.execute(
            f"""
            UPDATE knowledge_entries
            SET review_status = ?, publication_layer = ?, invalidated = 0
            WHERE document_id IN ({placeholders})
            """,
            [VALIDATED_REVIEW_STATUS, VALIDATED_PUBLICATION_LAYER, *doc_ids],
        )
        connection.commit()
        return {
            "database": str(database),
            "promoted_documents": len(doc_ids),
            "promoted_knowledge_entries": knowledge_count,
            "documents": [dict(row) for row in docs],
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "review_status": VALIDATED_REVIEW_STATUS,
            "publication_layer": VALIDATED_PUBLICATION_LAYER,
        }


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="将法律/行政法规提升为正式依据层")
    parser.add_argument(
        "--database",
        type=Path,
        default=project_root / "data" / "transport_safety_kb.sqlite3",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=project_root / "data" / "reports" / "promote_formal_laws_report.json",
    )
    args = parser.parse_args()
    result = promote(args.database)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"[>] report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
