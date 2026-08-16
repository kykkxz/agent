from __future__ import annotations

import os
import re
from pathlib import Path


_NON_ASCII = re.compile(r"[^\x00-\x7F]")


def path_has_non_ascii(path: Path | str) -> bool:
    return bool(_NON_ASCII.search(str(path)))


def windows_short_path(path: Path) -> Path:
    """Return 8.3 short path on Windows when available.

    Important: do not call Path.resolve() on the result. On Windows, resolve()
    expands 8.3 names back into the long Unicode path, which breaks Chroma HNSW.
    """
    if os.name != "nt":
        return path
    import ctypes
    from ctypes import wintypes

    # absolute() keeps 8.3 components; resolve() would expand them.
    resolved = str(Path(path).absolute())
    GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
    GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    GetShortPathNameW.restype = wintypes.DWORD
    length = GetShortPathNameW(resolved, ctypes.create_unicode_buffer(0), 0)
    if length == 0:
        return Path(resolved)
    buffer = ctypes.create_unicode_buffer(length)
    result = GetShortPathNameW(resolved, buffer, length)
    if result == 0:
        return Path(resolved)
    return Path(buffer.value)


def chroma_safe_path(path: Path | str, *, create: bool = True) -> Path:
    """Return a filesystem path safe for Chroma/hnswlib on Windows.

    Chroma's native HNSW segment fails to write/load under non-ASCII paths.
    Prefer Windows 8.3 short paths so the repo can remain under Chinese folders.
    """
    target = Path(path)
    if create:
        target.mkdir(parents=True, exist_ok=True)
    absolute = target.absolute()
    if not path_has_non_ascii(absolute):
        return absolute
    if os.name != "nt":
        raise RuntimeError(
            "Chroma persist directory contains non-ASCII characters and this platform "
            f"cannot rewrite it to a short path: {absolute}"
        )
    if not absolute.exists():
        absolute.mkdir(parents=True, exist_ok=True)
    short = windows_short_path(absolute)
    if path_has_non_ascii(short):
        fallback = Path("H:/wd/tskb-artifacts") / absolute.name
        fallback.mkdir(parents=True, exist_ok=True)
        pointer_dir = absolute if absolute.is_dir() else absolute.parent
        pointer_dir.mkdir(parents=True, exist_ok=True)
        pointer_dir.joinpath("CHROMA_PATH.txt").write_text(
            str(fallback.absolute()) + "\n", encoding="utf-8"
        )
        return fallback.absolute()
    return short
