from __future__ import annotations

import unittest
from pathlib import Path

from transport_kb.rag_paths import chroma_safe_path, path_has_non_ascii


class RagPathTests(unittest.TestCase):
    def test_detects_non_ascii(self) -> None:
        self.assertTrue(path_has_non_ascii(Path(r"H:\wd\新建文件夹\data")))
        self.assertFalse(path_has_non_ascii(Path(r"H:\wd\tskb\data")))

    def test_chroma_safe_path_is_ascii_on_windows(self) -> None:
        target = Path(__file__).resolve().parents[1] / "data" / "rag_path_probe"
        safe = chroma_safe_path(target, create=True)
        self.assertFalse(path_has_non_ascii(safe))
        self.assertTrue(safe.exists() or Path(str(safe)).exists())
        # Must remain short-form ASCII and not be expanded by resolve().
        self.assertFalse(path_has_non_ascii(str(safe)))


if __name__ == "__main__":
    unittest.main()
