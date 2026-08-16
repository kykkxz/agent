from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path
from typing import Any, Iterable

from .models import EvidenceUnit, KnowledgeEntry, SourceCandidate, StandardDocument


SCHEMA_VERSION = "2"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def _create_schema(connection: sqlite3.Connection) -> bool:
    connection.executescript(
        """
        CREATE TABLE schema_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE collection_runs (
            task_id TEXT PRIMARY KEY,
            completed_at TEXT NOT NULL,
            summary_json TEXT NOT NULL
        );
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY,
            plugin TEXT NOT NULL,
            source_uri TEXT NOT NULL,
            title TEXT NOT NULL,
            publisher TEXT NOT NULL,
            document_type TEXT NOT NULL,
            authority_level TEXT NOT NULL,
            version_status TEXT NOT NULL,
            extra_json TEXT NOT NULL
        );
        CREATE TABLE raw_assets (
            raw_asset_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL REFERENCES collection_runs(task_id),
            source_id TEXT NOT NULL REFERENCES sources(source_id),
            requested_uri TEXT NOT NULL,
            final_uri TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            media_type TEXT NOT NULL,
            raw_sha256 TEXT NOT NULL,
            raw_path TEXT NOT NULL,
            archive_metadata_path TEXT NOT NULL,
            transport TEXT NOT NULL,
            transport_note TEXT NOT NULL
        );
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL REFERENCES sources(source_id),
            raw_asset_id TEXT NOT NULL REFERENCES raw_assets(raw_asset_id),
            title TEXT NOT NULL,
            document_type TEXT NOT NULL,
            published_at TEXT NOT NULL,
            effective_from TEXT NOT NULL,
            effective_to TEXT NOT NULL,
            version_status TEXT NOT NULL,
            jurisdiction TEXT NOT NULL,
            applicable_roles_json TEXT NOT NULL,
            applicable_activities_json TEXT NOT NULL,
            license_status TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            section_locator TEXT NOT NULL,
            review_status TEXT NOT NULL,
            publication_layer TEXT NOT NULL,
            text TEXT NOT NULL,
            fetch_status TEXT NOT NULL,
            governance_notes_json TEXT NOT NULL
        );
        CREATE TABLE document_relations (
            relation_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
            relation_text TEXT NOT NULL
        );
        CREATE TABLE evidence_units (
            evidence_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
            locator TEXT NOT NULL,
            text TEXT NOT NULL,
            content_hash TEXT NOT NULL
        );
        CREATE TABLE knowledge_entries (
            knowledge_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
            topic TEXT NOT NULL,
            risk_categories_json TEXT NOT NULL,
            conclusion TEXT NOT NULL,
            review_status TEXT NOT NULL,
            publication_layer TEXT NOT NULL,
            invalidated INTEGER NOT NULL CHECK (invalidated IN (0, 1))
        );
        CREATE TABLE knowledge_citations (
            knowledge_id TEXT NOT NULL REFERENCES knowledge_entries(knowledge_id) ON DELETE CASCADE,
            citation_order INTEGER NOT NULL,
            evidence_id TEXT NOT NULL REFERENCES evidence_units(evidence_id),
            PRIMARY KEY (knowledge_id, citation_order)
        );
        CREATE TABLE quarantine (
            quarantine_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL REFERENCES collection_runs(task_id),
            source_id TEXT,
            record_json TEXT NOT NULL
        );
        CREATE TABLE collection_failures (
            failure_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL REFERENCES collection_runs(task_id),
            stage TEXT NOT NULL,
            source_id TEXT,
            record_json TEXT NOT NULL
        );

        CREATE INDEX idx_sources_document_type ON sources(document_type);
        CREATE INDEX idx_sources_authority ON sources(authority_level);
        CREATE INDEX idx_raw_assets_source_id ON raw_assets(source_id);
        CREATE INDEX idx_raw_assets_sha256 ON raw_assets(raw_sha256);
        CREATE INDEX idx_documents_source_id ON documents(source_id);
        CREATE INDEX idx_documents_document_type ON documents(document_type);
        CREATE INDEX idx_documents_version_status ON documents(version_status);
        CREATE INDEX idx_documents_review_status ON documents(review_status);
        CREATE INDEX idx_evidence_document_id ON evidence_units(document_id);
        CREATE INDEX idx_evidence_content_hash ON evidence_units(content_hash);
        CREATE INDEX idx_knowledge_document_id ON knowledge_entries(document_id);
        CREATE INDEX idx_knowledge_review_status ON knowledge_entries(review_status);
        CREATE INDEX idx_knowledge_citations_evidence_id ON knowledge_citations(evidence_id);
        """
    )
    try:
        connection.execute(
            "CREATE VIRTUAL TABLE knowledge_fts USING fts5(knowledge_id UNINDEXED, topic, conclusion)"
        )
        return True
    except sqlite3.OperationalError:
        connection.executescript(
            """
            CREATE TABLE knowledge_fts (
                knowledge_id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                conclusion TEXT NOT NULL
            );
            CREATE INDEX idx_knowledge_fts_topic ON knowledge_fts(topic);
            """
        )
        return False


def rebuild_database(
    database_path: Path,
    task_id: str,
    summary: dict[str, Any],
    candidates: Iterable[SourceCandidate],
    raw_records: Iterable[dict[str, Any]],
    documents: Iterable[StandardDocument],
    evidence: Iterable[EvidenceUnit],
    knowledge: Iterable[KnowledgeEntry],
    quarantine: Iterable[dict[str, Any]],
    failures: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Build a complete database off to the side, verify it, then replace the target."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = database_path.with_name(f".{database_path.name}.{uuid.uuid4().hex}.tmp")
    candidates = list(candidates)
    raw_records = list(raw_records)
    documents = list(documents)
    evidence = list(evidence)
    knowledge = list(knowledge)
    quarantine = list(quarantine)
    failures = list(failures)
    raw_asset_ids = {
        (item["source_id"], item["raw_path"]): _stable_id(
            "raw", f"{task_id}:{item['source_id']}:{item['raw_sha256']}"
        )
        for item in raw_records
    }
    try:
        with closing(sqlite3.connect(temp_path)) as connection, connection:
            connection.execute("PRAGMA foreign_keys = ON")
            fts5_available = _create_schema(connection)
            connection.executemany(
                "INSERT INTO schema_metadata(key, value) VALUES (?, ?)",
                [
                    ("schema_version", SCHEMA_VERSION),
                    ("fts5_available", "1" if fts5_available else "0"),
                    ("review_status", "机器初审/待核验层"),
                ],
            )
            connection.execute(
                "INSERT INTO collection_runs(task_id, completed_at, summary_json) VALUES (?, ?, ?)",
                (task_id, summary["started_and_completed_at"], _json(summary)),
            )
            connection.executemany(
                """
                INSERT INTO sources(
                    source_id, plugin, source_uri, title, publisher, document_type,
                    authority_level, version_status, extra_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.source_id,
                        item.plugin,
                        item.source_uri,
                        item.title,
                        item.publisher,
                        item.document_type,
                        item.authority_level,
                        item.version_status,
                        _json(_candidate_extra(item)),
                    )
                    for item in candidates
                ],
            )
            connection.executemany(
                """
                INSERT INTO raw_assets(
                    raw_asset_id, task_id, source_id, requested_uri, final_uri,
                    retrieved_at, status_code, media_type, raw_sha256, raw_path,
                    archive_metadata_path, transport, transport_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        _stable_id("raw", f"{task_id}:{item['source_id']}:{item['raw_sha256']}"),
                        task_id,
                        item["source_id"],
                        item["requested_uri"],
                        item["final_uri"],
                        item["retrieved_at"],
                        item["status_code"],
                        item["media_type"],
                        item["raw_sha256"],
                        item["raw_path"],
                        item["archive_metadata_path"],
                        item["transport"],
                        item.get("transport_note", ""),
                    )
                    for item in raw_records
                ],
            )
            connection.executemany(
                """
                INSERT INTO documents(
                    document_id, source_id, raw_asset_id, title, document_type,
                    published_at, effective_from, effective_to, version_status, jurisdiction,
                    applicable_roles_json, applicable_activities_json, license_status,
                    content_hash, retrieved_at, section_locator, review_status,
                    publication_layer, text, fetch_status, governance_notes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.document_id, item.source_id,
                        raw_asset_ids[(item.source_id, item.raw_path)], item.title,
                        item.document_type, item.published_at,
                        item.effective_from, item.effective_to, item.version_status,
                        item.jurisdiction, _json(item.applicable_role),
                        _json(item.applicable_activity), item.license_status,
                        item.content_hash, item.retrieved_at,
                        item.section_locator, item.review_status, item.publication_layer,
                        item.text, item.fetch_status,
                        _json(item.governance_notes),
                    )
                    for item in documents
                ],
            )
            connection.executemany(
                "INSERT INTO document_relations(relation_id, document_id, relation_text) VALUES (?, ?, ?)",
                [
                    (_stable_id("rel", f"{item.document_id}:{item.relation}"), item.document_id, item.relation)
                    for item in documents if item.relation
                ],
            )
            connection.executemany(
                """
                INSERT INTO evidence_units(
                    evidence_id, document_id, locator, text, content_hash
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.evidence_id, item.document_id, item.locator, item.text,
                        item.content_hash,
                    )
                    for item in evidence
                ],
            )
            connection.executemany(
                """
                INSERT INTO knowledge_entries(
                    knowledge_id, document_id, topic, risk_categories_json, conclusion,
                    review_status, publication_layer, invalidated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.knowledge_id, item.document_id, item.topic,
                        _json(item.risk_categories), item.conclusion, item.review_status,
                        item.publication_layer, int(item.invalidated),
                    )
                    for item in knowledge
                ],
            )
            connection.executemany(
                """
                INSERT INTO knowledge_citations(
                    knowledge_id, citation_order, evidence_id
                ) VALUES (?, ?, ?)
                """,
                [
                    (
                        item.knowledge_id, index, citation["evidence_id"],
                    )
                    for item in knowledge
                    for index, citation in enumerate(item.citations, 1)
                ],
            )
            connection.executemany(
                "INSERT INTO knowledge_fts(knowledge_id, topic, conclusion) VALUES (?, ?, ?)",
                [(item.knowledge_id, item.topic, item.conclusion) for item in knowledge],
            )
            connection.executemany(
                "INSERT INTO quarantine(quarantine_id, task_id, source_id, record_json) VALUES (?, ?, ?, ?)",
                [
                    (
                        item.get("document_id") or _stable_id("q", _json(item)),
                        task_id,
                        item.get("source_id"),
                        _json(item),
                    )
                    for item in quarantine
                ],
            )
            connection.executemany(
                "INSERT INTO collection_failures(task_id, stage, source_id, record_json) VALUES (?, ?, ?, ?)",
                [
                    (task_id, item.get("stage", "unknown"), item.get("source_id"), _json(item))
                    for item in failures
                ],
            )
        verification = verify_database(temp_path)
        if verification["integrity_check"] != ["ok"] or verification["foreign_key_violations"]:
            raise RuntimeError(f"SQLite verification failed: {verification}")
        os.replace(temp_path, database_path)
        return verify_database(database_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def migrate_database(database_path: Path) -> dict[str, Any]:
    """Migrate the v1 database to the normalized v2 schema without recollection."""
    database_path = database_path.resolve()
    temp_path = database_path.with_name(f".{database_path.name}.{uuid.uuid4().hex}.tmp")
    old = sqlite3.connect(database_path)
    new = sqlite3.connect(temp_path)
    try:
        old.row_factory = sqlite3.Row
        new.execute("PRAGMA foreign_keys = ON")
        fts5_available = _create_schema(new)
        schema_version = old.execute(
            "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
        ).fetchone()[0]
        if schema_version != "1":
            raise ValueError(f"仅支持从 SQLite 模式 1 迁移，当前为 {schema_version}")
        new.executemany(
            "INSERT INTO schema_metadata(key, value) VALUES (?, ?)",
            [("schema_version", SCHEMA_VERSION), ("fts5_available", "1" if fts5_available else "0"),
             ("review_status", "机器初审/待核验层")],
        )
        new.executemany(
            "INSERT INTO collection_runs(task_id, completed_at, summary_json) VALUES (?, ?, ?)",
            [(r["task_id"], r["completed_at"], r["summary_json"]) for r in old.execute("SELECT * FROM collection_runs")],
        )
        new.executemany(
            "INSERT INTO sources(source_id, plugin, source_uri, title, publisher, document_type, authority_level, version_status, extra_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(r["source_id"], r["plugin"], r["source_uri"], r["title"], r["publisher"], r["document_type"], r["authority_level"], r["version_status"], _source_extra(r["metadata_json"])) for r in old.execute("SELECT * FROM sources")],
        )
        raw_rows = old.execute("SELECT * FROM raw_assets").fetchall()
        raw_asset_ids = {(r["source_id"], r["raw_path"]): _stable_id("raw", f"{r['task_id']}:{r['source_id']}:{r['raw_sha256']}") for r in raw_rows}
        new.executemany(
            "INSERT INTO raw_assets(raw_asset_id, task_id, source_id, requested_uri, final_uri, retrieved_at, status_code, media_type, raw_sha256, raw_path, archive_metadata_path, transport, transport_note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(raw_asset_ids[(r["source_id"], r["raw_path"])], r["task_id"], r["source_id"], r["requested_uri"], r["final_uri"], r["retrieved_at"], r["status_code"], r["media_type"], r["raw_sha256"], r["raw_path"], r["archive_metadata_path"], r["transport"], r["transport_note"]) for r in raw_rows],
        )
        new.executemany(
            "INSERT INTO documents(document_id, source_id, raw_asset_id, title, document_type, published_at, effective_from, effective_to, version_status, jurisdiction, applicable_roles_json, applicable_activities_json, license_status, content_hash, retrieved_at, section_locator, review_status, publication_layer, text, fetch_status, governance_notes_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(r["document_id"], r["source_id"], raw_asset_ids[(r["source_id"], r["raw_path"])], r["title"], r["document_type"], r["published_at"], r["effective_from"], r["effective_to"], r["version_status"], r["jurisdiction"], r["applicable_roles_json"], r["applicable_activities_json"], r["license_status"], r["content_hash"], r["retrieved_at"], r["section_locator"], r["review_status"], r["publication_layer"], r["text"], r["fetch_status"], r["governance_notes_json"]) for r in old.execute("SELECT * FROM documents")],
        )
        new.executemany(
            "INSERT INTO document_relations(relation_id, document_id, relation_text) VALUES (?, ?, ?)",
            [(r["relation_id"], r["document_id"], r["relation_text"])
             for r in old.execute("SELECT relation_id, document_id, relation_text FROM document_relations")],
        )
        new.executemany(
            "INSERT INTO evidence_units(evidence_id, document_id, locator, text, content_hash) VALUES (?, ?, ?, ?, ?)",
            [(r["evidence_id"], r["document_id"], r["locator"], r["text"], r["content_hash"])
             for r in old.execute("SELECT evidence_id, document_id, locator, text, content_hash FROM evidence_units")],
        )
        new.executemany(
            "INSERT INTO knowledge_entries(knowledge_id, document_id, topic, risk_categories_json, conclusion, review_status, publication_layer, invalidated) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(r["knowledge_id"], r["document_id"], r["topic"], r["risk_categories_json"], r["conclusion"], r["review_status"], r["publication_layer"], r["invalidated"])
             for r in old.execute("SELECT knowledge_id, document_id, topic, risk_categories_json, conclusion, review_status, publication_layer, invalidated FROM knowledge_entries")],
        )
        new.executemany(
            "INSERT INTO knowledge_citations(knowledge_id, citation_order, evidence_id) VALUES (?, ?, ?)",
            [(r["knowledge_id"], r["citation_order"], r["evidence_id"])
             for r in old.execute("SELECT knowledge_id, citation_order, evidence_id FROM knowledge_citations")],
        )
        new.execute(
            "INSERT INTO knowledge_fts(knowledge_id, topic, conclusion) SELECT knowledge_id, topic, conclusion FROM knowledge_entries"
        )
        for table, columns in (("quarantine", ("quarantine_id", "task_id", "source_id", "record_json")), ("collection_failures", ("failure_id", "task_id", "stage", "source_id", "record_json"))):
            placeholders = ", ".join("?" for _ in columns)
            new.executemany(f"INSERT INTO {table}({', '.join(columns)}) VALUES ({placeholders})", [tuple(r[c] for c in columns) for r in old.execute(f"SELECT {', '.join(columns)} FROM {table}")])
        new.commit()
        old.close()
        old = None
        new.close()
        new = None
        verification = verify_database(temp_path)
        if verification["integrity_check"] != ["ok"] or verification["foreign_key_violations"]:
            raise RuntimeError(f"SQLite migration verification failed: {verification}")
        os.replace(temp_path, database_path)
        return verify_database(database_path)
    finally:
        if old is not None:
            old.close()
        if new is not None:
            new.close()
        if temp_path.exists():
            temp_path.unlink()


def _source_extra(metadata_json: str) -> str:
    metadata = json.loads(metadata_json)
    base_fields = {
        "source_id", "plugin", "source_uri", "title", "publisher", "document_type",
        "authority_level", "version_status", "published_at", "effective_from",
        "effective_to", "jurisdiction", "applicable_role", "applicable_activity",
        "license_status",
    }
    return _json({key: value for key, value in metadata.items() if key not in base_fields})


def _candidate_extra(item: SourceCandidate) -> dict[str, Any]:
    return {
        "expected_keywords": item.expected_keywords,
        "indexed_content": item.indexed_content,
        "relation": item.relation,
        "extra": item.extra,
    }


def verify_database(database_path: Path) -> dict[str, Any]:
    with closing(
        sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
    ) as connection:
        integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
        foreign_keys = [list(row) for row in connection.execute("PRAGMA foreign_key_check")]
        schema_version = connection.execute(
            "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
        ).fetchone()[0]
        fts5_available = connection.execute(
            "SELECT value FROM schema_metadata WHERE key = 'fts5_available'"
        ).fetchone()[0] == "1"
        tables = (
            "sources", "raw_assets", "documents", "evidence_units", "knowledge_entries",
            "knowledge_citations", "quarantine", "collection_failures",
        )
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in tables
        }
    return {
        "database": str(database_path),
        "schema_version": schema_version,
        "fts5_available": fts5_available,
        "integrity_check": integrity,
        "foreign_key_violations": foreign_keys,
        "counts": counts,
    }
