from __future__ import annotations

import unittest

from transport_kb.search import search


def entry(topic: str, conclusion: str, document_type: str) -> dict:
    return {
        "topic": topic,
        "conclusion": conclusion,
        "document_type": document_type,
        "citations": [{"source_uri": "https://www.gov.cn/source"}],
    }


class AuthorityAwareSearchRankingTests(unittest.TestCase):
    def test_special_operation_question_prefers_safety_production_law(self) -> None:
        entries = [
            entry("企业特种作业管理制度 / 第一条", "特种作业人员上岗要求和管理要求", "企业制度"),
            entry("中华人民共和国安全生产法 / 第三十条", "特种作业人员应经专门培训并取得相应资格后上岗", "法律"),
        ]
        matches = search(entries, "特种作业人员上岗有什么要求？", 2)
        self.assertIn("安全生产法", matches[0]["topic"])

    def test_supervision_question_prefers_construction_safety_regulation(self) -> None:
        entries = [
            entry("项目监理安全制度 / 第一条", "监理单位发现事故隐患后开展现场处理", "企业制度"),
            entry("建设工程安全生产管理条例 / 第十四条", "监理单位发现安全事故隐患应要求施工单位整改", "行政法规"),
        ]
        matches = search(entries, "监理单位发现安全事故隐患应如何处理？", 2)
        self.assertIn("建设工程安全生产管理条例", matches[0]["topic"])


if __name__ == "__main__":
    unittest.main()
