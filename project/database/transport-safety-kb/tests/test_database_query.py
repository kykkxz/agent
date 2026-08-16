from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from transport_kb.database_query import (
    QueryError,
    list_tables,
    open_read_only,
    read_rows,
    run_interactive,
    search_tables,
    table_schema,
)


class DatabaseQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.database = Path(self.directory.name) / "test.sqlite3"
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE documents (
                    document_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    document_type TEXT NOT NULL
                );
                CREATE TABLE collection_failures (
                    failure_id INTEGER PRIMARY KEY,
                    stage TEXT NOT NULL
                );
                INSERT INTO documents VALUES ('doc-1', '隧道施工安全规程', '操作规程');
                INSERT INTO documents VALUES ('doc-2', '安全生产法', '法律');
                """
            )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_lists_business_tables_with_counts(self) -> None:
        with closing(open_read_only(self.database)) as connection:
            tables = list_tables(connection)
        self.assertEqual([item["name"] for item in tables], ["collection_failures", "documents"])
        self.assertEqual(tables[1]["row_count"], 2)

    def test_reads_schema_and_filtered_rows(self) -> None:
        with closing(open_read_only(self.database)) as connection:
            schema = table_schema(connection, "documents")
            rows = read_rows(
                connection, "documents", limit=10, offset=0, filters=["document_type=法律"]
            )
        self.assertEqual(schema[1]["name"], "title")
        self.assertEqual(rows, [{"document_id": "doc-2", "title": "安全生产法", "document_type": "法律"}])

    def test_searches_all_business_tables(self) -> None:
        with closing(open_read_only(self.database)) as connection:
            results = search_tables(connection, "隧道", limit=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["table"], "documents")
        self.assertEqual(results[0]["row"]["document_id"], "doc-1")

    def test_rejects_unknown_table_and_column(self) -> None:
        with closing(open_read_only(self.database)) as connection:
            with self.assertRaises(QueryError):
                read_rows(connection, "missing", limit=10, offset=0)
            with self.assertRaises(QueryError):
                read_rows(connection, "documents", limit=10, offset=0, filters=["missing=x"])

    def test_connection_is_read_only(self) -> None:
        with (
            closing(open_read_only(self.database)) as connection,
            self.assertRaises(sqlite3.OperationalError),
        ):
            connection.execute("DELETE FROM documents")

    def test_interactive_menu_can_exit_cleanly(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, width=100)
        with (
            closing(open_read_only(self.database)) as connection,
            patch("transport_kb.database_query.Prompt.ask", return_value="0"),
        ):
            result = run_interactive(connection, self.database, console)
        self.assertEqual(result, 0)
        self.assertIn("交通建设与运营安全知识库", output.getvalue())
        self.assertIn("已退出", output.getvalue())

    def test_interactive_menu_searches_and_returns(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, width=100)
        with (
            closing(open_read_only(self.database)) as connection,
            patch(
                "transport_kb.database_query.Prompt.ask",
                side_effect=["2", "隧道", "1", "0"],
            ),
            patch("transport_kb.database_query.IntPrompt.ask", return_value=0),
        ):
            result = run_interactive(connection, self.database, console)
        self.assertEqual(result, 0)
        self.assertIn("隧道施工安全规程", output.getvalue())


if __name__ == "__main__":
    unittest.main()
