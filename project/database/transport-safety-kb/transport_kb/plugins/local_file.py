from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from ..models import FetchResult, SourceCandidate
from .base import SourcePlugin


class LocalFilePlugin(SourcePlugin):
    """Read configured local source files without modifying them."""

    plugin_name = "local_file_plugin"

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def discover(self, config: dict[str, Any]) -> list[SourceCandidate]:
        candidates: list[SourceCandidate] = []
        for item in config.get("sources", []):
            relative_path = Path(item["path"])
            if relative_path.is_absolute():
                path = relative_path.resolve()
            else:
                path = (self.project_root / relative_path).resolve()
            if not path.is_file():
                raise FileNotFoundError(f"configured local source does not exist: {path}")
            metadata = {key: value for key, value in item.items() if key != "path"}
            extra = dict(metadata.pop("extra", {}))
            extra.update({"local_primary_source": True, "local_path": str(path)})
            candidates.append(
                SourceCandidate(
                    plugin=self.plugin_name,
                    source_uri=path.as_uri(),
                    extra=extra,
                    **metadata,
                )
            )
        return candidates

    def fetch(self, candidate: SourceCandidate) -> FetchResult:
        path = Path(candidate.extra["local_path"])
        try:
            content = path.read_bytes()
        except OSError as exc:
            return FetchResult(
                candidate.source_uri,
                candidate.source_uri,
                0,
                "application/octet-stream",
                b"",
                "local-file",
                str(exc),
            )
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content.startswith(b"%PDF"):
            media_type = "application/pdf"
        return FetchResult(
            candidate.source_uri,
            candidate.source_uri,
            200,
            media_type,
            content,
            "local-file",
        )
