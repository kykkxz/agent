from __future__ import annotations

import unittest

from transport_kb.governance import SourceGovernance
from transport_kb.models import SourceCandidate, StandardDocument
from transport_kb.pipeline import split_evidence
from transport_kb.search import search


class GovernanceTests(unittest.TestCase):
    def test_rejects_non_whitelisted_domain(self) -> None:
        candidate = SourceCandidate(
            source_id="x", plugin="test", source_uri="https://example.com/a", title="安全生产法",
            publisher="测试", document_type="法律", published_at="2021-06-10",
            expected_keywords=["安全生产法"],
        )
        decision = SourceGovernance(["gov.cn"], 10).evaluate(candidate, "安全生产法正文足够长", candidate.title)
        self.assertFalse(decision.accepted)
        self.assertIn("来源域名不在白名单", decision.notes[0])

    def test_accepts_complete_official_source(self) -> None:
        candidate = SourceCandidate(
            source_id="x", plugin="test", source_uri="https://www.gov.cn/a", title="安全生产法",
            publisher="全国人大", document_type="法律", published_at="2021-06-10",
            expected_keywords=["安全生产法"],
        )
        decision = SourceGovernance(["gov.cn"], 10).evaluate(candidate, "安全生产法正文足够长", candidate.title)
        self.assertTrue(decision.accepted)


class EvidenceTests(unittest.TestCase):
    def test_splits_legal_articles(self) -> None:
        document = StandardDocument(
            document_id="doc", source_id="source", source_uri="https://www.gov.cn/a",
            title="测试法", publisher="全国人大", document_type="法律", published_at="2021-01-01",
            effective_from="", effective_to="", version_status="当前有效", jurisdiction="国家",
            applicable_role=[], applicable_activity=[], authority_level="A", license_status="公开发布",
            content_hash="hash", retrieved_at="now", section_locator="HTML", review_status="机器初审",
            publication_layer="待核验层", raw_path="raw/a", text="第一条 这是第一条足够长的测试正文内容。\n第二条 这是第二条足够长的测试正文内容。",
            fetch_status="test",
        )
        units = split_evidence(document)
        self.assertEqual([unit.locator for unit in units], ["第一条", "第二条"])


class SearchTests(unittest.TestCase):
    def test_returns_cited_result(self) -> None:
        entries = [{
            "topic": "安全生产法 / 第一条", "conclusion": "生产经营单位承担安全生产主体责任",
            "citations": [{"source_uri": "https://www.gov.cn/a"}],
        }]
        matches = search(entries, "安全生产责任", 5)
        self.assertEqual(len(matches), 1)

    def test_uncovered_accident_report_returns_no_result(self) -> None:
        entries = [{
            "topic": "安全生产法 / 第一条", "conclusion": "生产经营单位承担安全生产主体责任",
            "document_type": "法律", "citations": [{"source_uri": "https://www.gov.cn/a"}],
        }]
        self.assertEqual(search(entries, "典型交通事故的直接原因是什么", 5), [])

    def test_historical_version_is_excluded_from_default_search(self) -> None:
        entries = [{
            "topic": "旧法 / 第一条", "conclusion": "旧版本安全生产要求",
            "document_type": "法律", "invalidated": True,
            "citations": [{"source_uri": "https://www.gov.cn/old"}],
        }]
        self.assertEqual(search(entries, "安全生产要求", 5), [])


if __name__ == "__main__":
    unittest.main()
