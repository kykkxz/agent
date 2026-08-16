from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import discover_official_catalog as catalog
from transport_kb.models import FetchResult


INDEX_HTML = """
<html><body>
  <a href="/report/a.html">高速公路桥梁施工事故调查报告 2025-03-04</a>
  <a href="/report/b.html">道路运输车辆伤害事故调查报告 2025-03-05</a>
</body></html>
"""


class FakeTransport:
    def __init__(self) -> None:
        self.requested: list[str] = []

    def fetch(self, uri: str) -> FetchResult:
        self.requested.append(uri)
        return FetchResult(uri, uri, 200, "text/html", INDEX_HTML.encode("utf-8"), "fake")


class RecoverableCatalogDiscoveryTests(unittest.TestCase):
    def test_source_filter_and_limit_write_one_checkpoint_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "mem.jsonl"
            transport = FakeTransport()
            result = catalog.collect_source(
                "mem", transport=transport, checkpoint_path=checkpoint, limit=1
            )
            records = [json.loads(line) for line in checkpoint.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(result["written"], 1)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["source_uri"], "https://www.mem.gov.cn/report/a.html")
            self.assertTrue(all("/report/" not in uri for uri in transport.requested))

    def test_resume_does_not_duplicate_existing_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "mem.jsonl"
            transport = FakeTransport()
            catalog.collect_source("mem", transport=transport, checkpoint_path=checkpoint, limit=1)
            result = catalog.collect_source(
                "mem", transport=transport, checkpoint_path=checkpoint, limit=1
            )
            records = checkpoint.read_text(encoding="utf-8").splitlines()
            self.assertEqual(result["written"], 0)
            self.assertEqual(len(records), 1)

    def test_finalize_merges_and_sorts_checkpoint_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "a.jsonl"
            second = root / "b.jsonl"
            first.write_text(json.dumps({"source_uri": "https://x.gov.cn/z", "source_id": "z", "title": "乙"}, ensure_ascii=False) + "\n", encoding="utf-8")
            second.write_text(json.dumps({"source_uri": "https://x.gov.cn/a", "source_id": "a", "title": "甲"}, ensure_ascii=False) + "\n", encoding="utf-8")
            output = root / "generated.json"
            payload = catalog.finalize_catalog([first, second], output)
            self.assertEqual(payload["source_count"], 2)
            self.assertEqual([item["title"] for item in payload["sources"]], ["甲", "乙"])
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
