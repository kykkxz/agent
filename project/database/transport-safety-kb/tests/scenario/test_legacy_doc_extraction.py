from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from transport_kb.extractors import extract_content


OLE_HEADER = bytes.fromhex("d0cf11e0a1b11ae1") + b"legacy-word-body"


class FakeDocument:
    def __init__(self, text: str) -> None:
        self.Content = type("Content", (), {"Text": text})()
        self.closed = False

    def Close(self, save_changes: bool) -> None:
        self.closed = True


class FakeDocuments:
    def __init__(self, document: FakeDocument | None = None, error: Exception | None = None) -> None:
        self.document = document
        self.error = error
        self.opened_path = ""

    def Open(self, path: str, **_: object) -> FakeDocument:
        self.opened_path = path
        if self.error:
            raise self.error
        assert self.document is not None
        return self.document


class FakeWord:
    def __init__(self, documents: FakeDocuments) -> None:
        self.Documents = documents
        self.DisplayAlerts = None
        self.Visible = None
        self.quit_called = False

    def Quit(self) -> None:
        self.quit_called = True


class LegacyDocExtractionTests(unittest.TestCase):
    def test_extract_content_recognizes_ole_doc_and_closes_word(self) -> None:
        document = FakeDocument("综合应急预案\r道路运输突发事件应急预案\r")
        word = FakeWord(FakeDocuments(document=document))
        with patch("win32com.client.DispatchEx", return_value=word):
            _, text = extract_content("application/octet-stream", OLE_HEADER)
        self.assertIn("综合应急预案", text)
        self.assertTrue(document.closed)
        self.assertTrue(word.quit_called)
        self.assertFalse(Path(word.Documents.opened_path).exists())

    def test_word_is_closed_and_temp_file_removed_when_open_fails(self) -> None:
        documents = FakeDocuments(error=OSError("cannot open"))
        word = FakeWord(documents)
        with patch("win32com.client.DispatchEx", return_value=word):
            with self.assertRaisesRegex(RuntimeError, "legacy DOC extraction failed"):
                extract_content("application/msword", OLE_HEADER)
        self.assertTrue(word.quit_called)
        self.assertFalse(Path(documents.opened_path).exists())


if __name__ == "__main__":
    unittest.main()
