from __future__ import annotations

import unittest

from transport_kb import pipeline
from transport_kb.models import SourceCandidate


class FragmentedOfficialSourceTests(unittest.TestCase):
    def test_splits_exact_standalone_titles_without_overlap(self) -> None:
        candidate = SourceCandidate(
            source_id="bundle", plugin="test", source_uri="https://www.gov.cn/plans.doc",
            title="成套预案", publisher="测试机关", document_type="应急预案",
            extra={"split_titles": ["综合应急预案", "公路应急预案", "水路应急预案"]},
        )
        text = (
            "综合应急预案\n第一部分正文中提到公路应急预案但不是标题。\n"
            "公路应急预案\n第二部分正文。\n"
            "水路应急预案\n第三部分正文。"
        )
        fragments = pipeline.fragment_candidate_text(candidate, text)
        self.assertEqual([title for title, _ in fragments], candidate.extra["split_titles"])
        self.assertIn("第一部分正文", fragments[0][1])
        self.assertNotIn("第二部分正文", fragments[0][1])
        self.assertIn("第三部分正文", fragments[2][1])

    def test_returns_original_document_without_split_configuration(self) -> None:
        candidate = SourceCandidate(
            source_id="single", plugin="test", source_uri="https://www.gov.cn/one.html",
            title="单一预案", publisher="测试机关", document_type="应急预案",
        )
        self.assertEqual(
            pipeline.fragment_candidate_text(candidate, "单一预案\n正文"),
            [("单一预案", "单一预案\n正文")],
        )


if __name__ == "__main__":
    unittest.main()
