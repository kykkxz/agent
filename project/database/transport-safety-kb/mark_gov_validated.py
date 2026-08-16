from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


VALIDATED_REVIEW_STATUS = "通过校验"
VALIDATED_PUBLICATION_LAYER = "正式依据层"
GOV_DOMAIN = "gov.cn"


def is_gov_cn_uri(uri: str) -> bool:
    hostname = (urlparse(uri).hostname or "").lower().rstrip(".")
    return hostname == GOV_DOMAIN or hostname.endswith(f".{GOV_DOMAIN}")


def _gov_source_ids(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute("SELECT source_id, source_uri FROM sources").fetchall()
    return [source_id for source_id, source_uri in rows if is_gov_cn_uri(source_uri)]


def mark_database(database: Path) -> dict[str, int | str]:
    database = database.resolve()
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        source_ids = _gov_source_ids(connection)
        if not source_ids:
            return {
                "database": str(database),
                "gov_sources": 0,
                "validated_documents": 0,
                "validated_knowledge_entries": 0,
            }
        placeholders = ", ".join("?" for _ in source_ids)
        document_count = connection.execute(
            f"SELECT COUNT(*) FROM documents WHERE source_id IN ({placeholders})", source_ids
        ).fetchone()[0]
        knowledge_count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM knowledge_entries AS k
            JOIN documents AS d ON d.document_id = k.document_id
            WHERE d.source_id IN ({placeholders})
            """,
            source_ids,
        ).fetchone()[0]
        connection.execute(
            f"""
            UPDATE documents
            SET review_status = ?, publication_layer = ?
            WHERE source_id IN ({placeholders})
            """,
            [VALIDATED_REVIEW_STATUS, VALIDATED_PUBLICATION_LAYER, *source_ids],
        )
        connection.execute(
            f"""
            UPDATE knowledge_entries
            SET review_status = ?, publication_layer = ?
            WHERE document_id IN (
                SELECT document_id FROM documents WHERE source_id IN ({placeholders})
            )
            """,
            [VALIDATED_REVIEW_STATUS, VALIDATED_PUBLICATION_LAYER, *source_ids],
        )
        connection.commit()
        return {
            "database": str(database),
            "gov_sources": len(source_ids),
            "validated_documents": int(document_count),
            "validated_knowledge_entries": int(knowledge_count),
        }


def _update_jsonl(path: Path, document_status: dict[str, tuple[str, str]]) -> int:
    if not path.exists():
        return 0
    updated = 0
    records = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            document_id = record.get("document_id")
            if document_id in document_status:
                record["review_status"], record["publication_layer"] = document_status[document_id]
                updated += 1
            records.append(record)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return updated


def update_exports(output: Path, database: Path) -> dict[str, int]:
    with sqlite3.connect(database) as connection:
        document_status = {
            document_id: (VALIDATED_REVIEW_STATUS, VALIDATED_PUBLICATION_LAYER)
            for document_id, source_id in connection.execute(
                "SELECT document_id, source_id FROM documents"
            ).fetchall()
            if source_id in set(_gov_source_ids(connection))
        }
    data_dir = output / "data"
    updated = {
        "documents_jsonl": _update_jsonl(data_dir / "documents.jsonl", document_status),
        "evidence_jsonl": 0,
        "knowledge_base_jsonl": _update_jsonl(data_dir / "knowledge_base.jsonl", document_status),
    }
    evidence_path = data_dir / "evidence.jsonl"
    if evidence_path.exists():
        records = []
        with evidence_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("document_id") in document_status:
                    record["review_status"] = VALIDATED_REVIEW_STATUS
                    updated["evidence_jsonl"] += 1
                records.append(record)
        with evidence_path.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return updated


def update_reports(output: Path, database: Path) -> dict[str, int]:
    data_dir = output / "data"
    report_dir = data_dir / "reports"
    updated = {"json_reports": 0, "markdown_reports": 0}
    for name in ("final_run_report.json", "run_summary.json"):
        path = report_dir / name
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "review_status" in payload:
            payload["review_status"] = (
                "gov.cn 来源已通过校验并进入正式依据层；其他来源保持原审核状态"
            )
        collection = payload.get("collection")
        if isinstance(collection, dict) and "review_status" in collection:
            collection["review_status"] = (
                "gov.cn 来源已通过校验并进入正式依据层；其他来源保持原审核状态"
            )
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        updated["json_reports"] += 1

    acceptance = report_dir / "acceptance_report.json"
    if acceptance.exists():
        payload = json.loads(acceptance.read_text(encoding="utf-8"))
        changed = 0
        for result in payload.get("results", []):
            for item in result.get("top_results", []):
                citations = item.get("citations", [])
                if any(is_gov_cn_uri(citation.get("source_uri", "")) for citation in citations):
                    item["review_status"] = VALIDATED_REVIEW_STATUS
                    item["publication_layer"] = VALIDATED_PUBLICATION_LAYER
                    changed += 1
        acceptance.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        updated["json_reports"] += 1

    registry = report_dir / "source_registry.md"
    if registry.exists():
        lines = registry.read_text(encoding="utf-8").splitlines()
        lines[2] = "gov.cn 及其子域来源已通过校验并进入正式依据层，其他来源保持原审核状态。"
        lines = [
            line.replace("已采集，待人工审核", "已通过校验，正式依据层")
            if "gov.cn" in line
            else line
            for line in lines
        ]
        registry.write_text("\n".join(lines) + "\n", encoding="utf-8")
        updated["markdown_reports"] += 1

    coverage = report_dir / "coverage_gap.md"
    if coverage.exists():
        text = coverage.read_text(encoding="utf-8")
        text = text.replace(
            "全部采集结果仍位于机器初审/待核验层，数量达标不等同于人工审核通过。",
            "gov.cn 及其子域来源已通过校验并进入正式依据层；其他来源仍位于机器初审/待核验层。",
        )
        coverage.write_text(text, encoding="utf-8")
        updated["markdown_reports"] += 1
    return updated


def backup_files(output: Path, stamp: str) -> list[str]:
    backup_dir = output / "data" / f"before_gov_validation_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    names = (
        "transport_safety_kb.sqlite3",
        "documents.jsonl",
        "evidence.jsonl",
        "knowledge_base.jsonl",
        "raw_manifest.jsonl",
    )
    copied = []
    for name in names:
        source = output / "data" / name
        if source.exists():
            target = backup_dir / name
            shutil.copy2(source, target)
            copied.append(str(target))
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description="将 gov.cn 来源标记为已通过校验")
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).resolve().parent
    )
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    copied = [] if args.no_backup else backup_files(output, stamp)
    database = output / "data" / "transport_safety_kb.sqlite3"
    result = mark_database(database)
    result["backups"] = len(copied)
    result["exports"] = update_exports(output, database)
    result["reports"] = update_reports(output, database)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
