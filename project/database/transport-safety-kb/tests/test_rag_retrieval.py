from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from langchain_core.documents import Document

from transport_kb.rag_retrieval import (
    SparseBM25Retriever,
    load_formal_evidence,
    reciprocal_rank_fusion,
    tokenize_for_bm25,
    validate_retrieved_ids,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE = PROJECT_ROOT / "data" / "transport_safety_kb.sqlite3"


class FakeRetriever:
    def __init__(self, docs: list[Document]):
        self.docs = docs
        self.k = 0

    def invoke(self, _query: str) -> list[Document]:
        return self.docs[: self.k]


class RagRetrievalTests(unittest.TestCase):
    def test_bm25_supports_chinese_bigrams(self) -> None:
        matching = Document(page_content="重大事故隐患应当及时排查治理")
        unrelated = Document(page_content="员工节日福利和生日福利")
        retriever = SparseBM25Retriever.from_documents([unrelated, matching])
        retriever.k = 1
        self.assertEqual(retriever.invoke("事故隐患排查"), [matching])
        self.assertIn("事故", tokenize_for_bm25("事故隐患"))
        self.assertIn("故隐", tokenize_for_bm25("事故隐患"))

    def test_rrf_preserves_shared_candidates(self) -> None:
        first = Document(page_content="第一", metadata={"evidence_id": "e1"})
        second = Document(page_content="第二", metadata={"evidence_id": "e2"})
        fused = reciprocal_rank_fusion(
            [([first, second], 1.0, "dense"), ([first], 1.0, "sparse")],
            rrf_k=60,
            top_k=2,
        )
        self.assertEqual([doc.metadata["evidence_id"] for doc in fused], ["e1", "e2"])
        self.assertEqual(fused[0].metadata["retrieval_ranks"], {"dense": 1, "sparse": 1})

    def test_formal_evidence_is_available_and_traceable(self) -> None:
        records = load_formal_evidence(DATABASE)
        self.assertGreaterEqual(len(records), 1282)
        self.assertIn("中华人民共和国安全生产法", {record["title"] for record in records})
        ids = [record["evidence_id"] for record in records[:5]]
        validated = validate_retrieved_ids(DATABASE, ids)
        self.assertEqual(set(validated), set(ids))
        self.assertTrue(all(item.publication_layer == "正式依据层" for item in validated.values()))
        self.assertTrue(all(item.review_status == "通过校验" for item in validated.values()))

    def test_invalid_hash_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "test.sqlite3"
            db = sqlite3.connect(database)
            try:
                db.executescript(
                    """
                    CREATE TABLE sources(source_id TEXT PRIMARY KEY, source_uri TEXT, publisher TEXT, authority_level TEXT);
                    CREATE TABLE documents(document_id TEXT PRIMARY KEY, source_id TEXT, title TEXT, document_type TEXT,
                        version_status TEXT, review_status TEXT, publication_layer TEXT, invalidated INTEGER);
                    CREATE TABLE evidence_units(evidence_id TEXT PRIMARY KEY, document_id TEXT, locator TEXT,
                        text TEXT, content_hash TEXT);
                    CREATE TABLE knowledge_entries(knowledge_id TEXT PRIMARY KEY, document_id TEXT,
                        topic TEXT, invalidated INTEGER, review_status TEXT, publication_layer TEXT);
                    CREATE TABLE knowledge_citations(knowledge_id TEXT, citation_order INTEGER, evidence_id TEXT);
                    INSERT INTO sources VALUES ('s', 'https://www.gov.cn/a', '机关', 'A');
                    INSERT INTO documents VALUES ('d', 's', '标题', '法律', '当前有效候选', '通过校验', '正式依据层', 0);
                    INSERT INTO evidence_units VALUES ('e', 'd', '第一条', '原文', 'wrong-hash');
                    INSERT INTO knowledge_entries VALUES ('k', 'd', '主题', 0, '通过校验', '正式依据层');
                    INSERT INTO knowledge_citations VALUES ('k', 1, 'e');
                    """
                )
                db.commit()
            finally:
                db.close()
            self.assertEqual(validate_retrieved_ids(database, ["e"]), {})


if __name__ == "__main__":
    unittest.main()
