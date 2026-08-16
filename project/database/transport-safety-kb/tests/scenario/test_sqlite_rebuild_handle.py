from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from transport_kb.sqlite_store import rebuild_database, verify_database


def rebuild_empty(path: Path) -> None:
    rebuild_database(
        database_path=path,
        task_id="test-run",
        summary={"started_and_completed_at": "2026-08-11T00:00:00+00:00"},
        candidates=[],
        raw_records=[],
        documents=[],
        evidence=[],
        knowledge=[],
        quarantine=[],
        failures=[],
    )


class SqliteHandleTests(unittest.TestCase):
    def test_rebuilds_same_path_twice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.sqlite3"
            rebuild_empty(path)
            rebuild_empty(path)
            self.assertEqual(verify_database(path)["integrity_check"], ["ok"])

    def test_verify_releases_database_for_rename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.sqlite3"
            renamed = Path(directory) / "renamed.sqlite3"
            rebuild_empty(path)
            verify_database(path)
            path.replace(renamed)
            self.assertTrue(renamed.is_file())


if __name__ == "__main__":
    unittest.main()
