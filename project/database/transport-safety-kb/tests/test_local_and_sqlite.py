from __future__ import annotations

import subprocess
import sqlite3
import sys
from contextlib import closing
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from transport_kb.extractors import extract_docx
from transport_kb.models import EvidenceUnit, KnowledgeEntry, SourceCandidate, StandardDocument
from transport_kb.pipeline import split_evidence
from transport_kb.plugins.local_file import LocalFilePlugin
from transport_kb.sqlite_store import migrate_database, rebuild_database


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DocxExtractionTests(unittest.TestCase):
    def test_extracts_paragraphs_from_office_document(self) -> None:
        content = BytesIO()
        with ZipFile(content, "w") as archive:
            archive.writestr(
                "word/document.xml",
                """<?xml version="1.0" encoding="UTF-8"?>
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                  <w:body><w:p><w:r><w:t>第一条 测试正文</w:t></w:r></w:p></w:body>
                </w:document>""",
            )
        _, text = extract_docx(content.getvalue())
        self.assertEqual(text, "第一条 测试正文")


class LocalFilePluginTests(unittest.TestCase):
    def test_discovers_and_fetches_configured_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "law.pdf"
            source.write_bytes(b"%PDF-test-source")
            plugin = LocalFilePlugin(root)
            candidates = plugin.discover({"sources": [{
                "path": "law.pdf", "source_id": "law", "title": "测试法",
                "publisher": "测试机关", "document_type": "法律",
                "published_at": "2021-01-01",
            }]})
            fetched = plugin.fetch(candidates[0])
            self.assertEqual(fetched.content, b"%PDF-test-source")
            self.assertEqual(fetched.media_type, "application/pdf")
            self.assertTrue(candidates[0].extra["local_primary_source"])

    def test_missing_configured_pdf_fails_fast(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = LocalFilePlugin(Path(directory))
            with self.assertRaises(FileNotFoundError):
                plugin.discover({"sources": [{
                    "path": "missing.pdf", "source_id": "missing", "title": "缺失",
                    "publisher": "测试机关", "document_type": "法律",
                }]})


class PdfEvidenceTests(unittest.TestCase):
    def test_locator_contains_pdf_page_and_article(self) -> None:
        document = StandardDocument(
            document_id="doc", source_id="source", source_uri="file:///law.pdf",
            title="测试法", publisher="测试机关", document_type="法律",
            published_at="2021-01-01", effective_from="", effective_to="",
            version_status="当前有效候选", jurisdiction="国家", applicable_role=[],
            applicable_activity=[], authority_level="A", license_status="公开发布",
            content_hash="hash", retrieved_at="now", section_locator="PDF页码与条款",
            review_status="机器初审", publication_layer="待核验层", raw_path="source_archive/a.pdf",
            text="[第1页]\n第一条 这是跨页条款的前半部分。\n[第2页]\n这是后半部分。\n第二条 这是第二条足够长度的测试正文内容。",
            fetch_status="local-file",
        )
        units = split_evidence(document)
        self.assertEqual(units[0].locator, "第1-2页 / 第一条")
        self.assertEqual(units[1].locator, "第2页 / 第二条")


class SqliteStoreTests(unittest.TestCase):
    def test_schema_counts_and_foreign_keys(self) -> None:
        candidate = SourceCandidate(
            source_id="source", plugin="test", source_uri="https://www.gov.cn/test",
            title="测试法", publisher="测试机关", document_type="法律",
        )
        document = StandardDocument(
            document_id="doc", source_id="source", source_uri=candidate.source_uri,
            title="测试法", publisher="测试机关", document_type="法律", published_at="2021-01-01",
            effective_from="", effective_to="", version_status="当前有效候选", jurisdiction="国家",
            applicable_role=[], applicable_activity=[], authority_level="A", license_status="公开发布",
            content_hash="hash", retrieved_at="now", section_locator="HTML", review_status="机器初审",
            publication_layer="待核验层", raw_path="source_archive/test.html", text="第一条 测试正文",
            fetch_status="test",
        )
        evidence = EvidenceUnit(
            evidence_id="ev", document_id="doc", source_uri=candidate.source_uri,
            title="测试法", locator="第一条", text="第一条 测试正文", content_hash="hash",
            authority_level="A", review_status="机器初审",
        )
        knowledge = KnowledgeEntry(
            knowledge_id="kb", topic="测试法 / 第一条", document_type="法律",
            version_status="当前有效候选", risk_categories=["综合安全管理"], applicable_roles=[],
            applicable_activities=[], conclusion="测试正文", authority_level="A",
            citations=[{"evidence_id": "ev", "source_uri": candidate.source_uri, "locator": "第一条"}],
            review_status="机器初审", publication_layer="待核验层", invalidated=False,
            document_id="doc",
        )
        with tempfile.TemporaryDirectory() as directory:
            result = rebuild_database(
                Path(directory) / "kb.sqlite3", "run",
                {"started_and_completed_at": "2026-08-11T00:00:00+00:00"},
                [candidate], [{
                    "source_id": "source", "requested_uri": candidate.source_uri,
                    "final_uri": candidate.source_uri, "retrieved_at": "now", "status_code": 200,
                    "media_type": "text/html", "raw_sha256": "rawhash",
                    "raw_path": "source_archive/test.html",
                    "archive_metadata_path": "source_archive/test.metadata.json",
                    "transport": "test", "transport_note": "",
                }], [document], [evidence], [knowledge], [], [],
            )
            self.assertEqual(result["integrity_check"], ["ok"])
            self.assertEqual(result["foreign_key_violations"], [])
            self.assertEqual(result["counts"]["knowledge_entries"], 1)
            self.assertEqual(result["counts"]["knowledge_citations"], 1)
            with closing(sqlite3.connect(Path(directory) / "kb.sqlite3")) as connection:
                columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(knowledge_entries)")
                }
                self.assertEqual(
                    columns,
                    {
                        "knowledge_id", "document_id", "topic", "risk_categories_json",
                        "conclusion", "review_status", "publication_layer", "invalidated",
                    },
                )
                citation_columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(knowledge_citations)")
                }
                self.assertEqual(citation_columns, {"knowledge_id", "citation_order", "evidence_id"})

    def test_migrates_v1_without_changing_business_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "v1.sqlite3"
            with closing(sqlite3.connect(database)) as connection:
                connection.executescript(
                    """
                    CREATE TABLE schema_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    CREATE TABLE collection_runs (task_id TEXT PRIMARY KEY, completed_at TEXT NOT NULL, summary_json TEXT NOT NULL);
                    CREATE TABLE sources (
                        source_id TEXT PRIMARY KEY, plugin TEXT NOT NULL, source_uri TEXT NOT NULL,
                        title TEXT NOT NULL, publisher TEXT NOT NULL, document_type TEXT NOT NULL,
                        authority_level TEXT NOT NULL, version_status TEXT NOT NULL, metadata_json TEXT NOT NULL
                    );
                    CREATE TABLE raw_assets (
                        raw_asset_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, source_id TEXT NOT NULL,
                        requested_uri TEXT NOT NULL, final_uri TEXT NOT NULL, retrieved_at TEXT NOT NULL,
                        status_code INTEGER NOT NULL, media_type TEXT NOT NULL, raw_sha256 TEXT NOT NULL,
                        raw_path TEXT NOT NULL, archive_metadata_path TEXT NOT NULL, transport TEXT NOT NULL,
                        transport_note TEXT NOT NULL
                    );
                    CREATE TABLE documents (
                        document_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, source_uri TEXT NOT NULL,
                        title TEXT NOT NULL, publisher TEXT NOT NULL, document_type TEXT NOT NULL,
                        published_at TEXT NOT NULL, effective_from TEXT NOT NULL, effective_to TEXT NOT NULL,
                        version_status TEXT NOT NULL, jurisdiction TEXT NOT NULL, applicable_roles_json TEXT NOT NULL,
                        applicable_activities_json TEXT NOT NULL, authority_level TEXT NOT NULL,
                        license_status TEXT NOT NULL, content_hash TEXT NOT NULL, retrieved_at TEXT NOT NULL,
                        section_locator TEXT NOT NULL, review_status TEXT NOT NULL, publication_layer TEXT NOT NULL,
                        raw_path TEXT NOT NULL, text TEXT NOT NULL, fetch_status TEXT NOT NULL,
                        governance_notes_json TEXT NOT NULL
                    );
                    CREATE TABLE document_relations (relation_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, relation_text TEXT NOT NULL);
                    CREATE TABLE evidence_units (
                        evidence_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, source_uri TEXT NOT NULL,
                        title TEXT NOT NULL, locator TEXT NOT NULL, text TEXT NOT NULL, content_hash TEXT NOT NULL,
                        authority_level TEXT NOT NULL, review_status TEXT NOT NULL
                    );
                    CREATE TABLE knowledge_entries (
                        knowledge_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, topic TEXT NOT NULL,
                        document_type TEXT NOT NULL, version_status TEXT NOT NULL, risk_categories_json TEXT NOT NULL,
                        applicable_roles_json TEXT NOT NULL, applicable_activities_json TEXT NOT NULL,
                        conclusion TEXT NOT NULL, authority_level TEXT NOT NULL, review_status TEXT NOT NULL,
                        publication_layer TEXT NOT NULL, invalidated INTEGER NOT NULL
                    );
                    CREATE TABLE knowledge_citations (
                        knowledge_id TEXT NOT NULL, citation_order INTEGER NOT NULL, evidence_id TEXT NOT NULL,
                        source_uri TEXT NOT NULL, locator TEXT NOT NULL, PRIMARY KEY (knowledge_id, citation_order)
                    );
                    CREATE TABLE quarantine (quarantine_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, source_id TEXT, record_json TEXT NOT NULL);
                    CREATE TABLE collection_failures (failure_id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, stage TEXT NOT NULL, source_id TEXT, record_json TEXT NOT NULL);
                    INSERT INTO schema_metadata VALUES ('schema_version', '1');
                    INSERT INTO schema_metadata VALUES ('fts5_available', '1');
                    INSERT INTO schema_metadata VALUES ('review_status', '机器初审/待核验层');
                    INSERT INTO collection_runs VALUES ('run', 'now', '{}');
                    INSERT INTO sources VALUES ('source', 'test', 'https://example.com', '测试法', '测试机关', '法律', 'A', '当前有效候选', '{"extra":{"x":1},"expected_keywords":["法"]}');
                    INSERT INTO raw_assets VALUES ('raw-old', 'run', 'source', 'https://example.com', 'https://example.com', 'now', 200, 'text/html', 'hash', 'raw/test.html', 'raw/test.json', 'test', '');
                    INSERT INTO documents VALUES ('doc', 'source', 'https://example.com', '测试法', '测试机关', '法律', '2021', '', '', '当前有效候选', '国家', '[]', '[]', 'A', '公开发布', 'doc-hash', 'now', 'HTML', '机器初审', '待核验层', 'raw/test.html', '正文', 'test', '[]');
                    INSERT INTO evidence_units VALUES ('ev', 'doc', 'https://example.com', '测试法', '第一条', '证据正文', 'ev-hash', 'A', '机器初审');
                    INSERT INTO knowledge_entries VALUES ('kb', 'doc', '测试法 / 第一条', '法律', '当前有效候选', '["综合安全管理"]', '[]', '[]', '知识正文', 'A', '机器初审', '待核验层', 0);
                    INSERT INTO knowledge_citations VALUES ('kb', 1, 'ev', 'https://example.com', '第一条');
                    """
                )
            result = migrate_database(database)
            self.assertEqual(result["schema_version"], "2")
            self.assertEqual(result["counts"]["documents"], 1)
            self.assertEqual(result["counts"]["evidence_units"], 1)
            self.assertEqual(result["counts"]["knowledge_entries"], 1)
            self.assertEqual(result["counts"]["knowledge_citations"], 1)


class ClosedLoopScriptTests(unittest.TestCase):
    def test_offline_mode_builds_database_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    sys.executable, str(PROJECT_ROOT / "run_pipeline.py"), "--offline",
                    "--manifest", str(PROJECT_ROOT / "config" / "sources.json"),
                    "--questions", str(PROJECT_ROOT / "config" / "acceptance_questions.json"),
                    "--output", directory,
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(directory) / "transport_safety_kb.sqlite3").is_file())
            self.assertTrue((Path(directory) / "reports" / "final_run_report.json").is_file())
            self.assertEqual(len(list((Path(directory) / "source_archive").rglob("*.pdf"))), 2)


if __name__ == "__main__":
    unittest.main()
